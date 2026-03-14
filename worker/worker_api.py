import json
import shutil
import tempfile
import threading
from pathlib import Path

from flask import Flask, after_this_request, jsonify, request, send_file
from werkzeug.utils import secure_filename

from analysis_client import analyze_observations
from config.aws import build_s3_object_url, s3_client
from config.reader import CONFIG, require_value
from pipeline.ocr_detect import extract_ocr_observations
from pipeline.upload_outputs import upload_clips_and_thumbnails
from pipeline.video_processing import (
    crop_killfeed_region,
    cut_planned_clips,
    download_video_from_s3,
    extract_sampled_frames,
    generate_clip_thumbnails,
    merge_local_clips,
)
from store import (
    create_job_record,
    delete_all_jobs as delete_all_jobs_record,
    delete_clip as delete_clip_record,
    get_clips_by_ids,
    get_clips_by_ids_any_video,
    list_all_clips,
    list_jobs_with_clips,
    replace_clips,
    save_job,
)
from utils.logger import get_logger

logger = get_logger("local-helper")
app = Flask(__name__)

FRAME_SAMPLE_FPS = CONFIG.getfloat("pipeline", "frame_sample_fps")
CROP_X = CONFIG.getint("pipeline", "crop_x")
CROP_Y = CONFIG.getint("pipeline", "crop_y")
CROP_W = CONFIG.getint("pipeline", "crop_w")
CROP_H = CONFIG.getint("pipeline", "crop_h")
FUZZY_MATCH_THRESHOLD = CONFIG.getint("pipeline", "fuzzy_match_threshold")
DEDUPE_WINDOW_SECONDS = CONFIG.getfloat("pipeline", "dedupe_window_seconds")
MERGE_WINDOW_SECONDS = CONFIG.getfloat("pipeline", "merge_window_seconds")
CLIP_PRE_SECONDS = CONFIG.getfloat("pipeline", "clip_pre_seconds")
CLIP_POST_SECONDS = CONFIG.getfloat("pipeline", "clip_post_seconds")
LOCAL_TEMP_DIR = require_value("local_helper", "temp_dir")
KEEP_JOB_ARTIFACTS = CONFIG.getboolean("local_helper", "keep_job_artifacts")
CORS_ALLOWED_ORIGIN = require_value("local_helper", "cors_allowed_origin")
MAX_CONCURRENT_JOBS = CONFIG.getint("local_helper", "max_concurrent_jobs")

_jobs: dict[str, dict] = {}
_lock = threading.Lock()

_STAGE_PROGRESS = {
    "queued": 0,
    "extracting_frames": 20,
    "cropping_killfeed": 35,
    "running_ocr": 55,
    "calling_analysis_api": 72,
    "cutting_clips": 88,
    "generating_thumbnails": 96,
    "uploading_to_s3": 98,
    "completed": 100,
    "failed": 100,
}


def _job_root(job_id: str) -> Path:
    return Path(LOCAL_TEMP_DIR) / f"job-{job_id}"

def _serialize_clip(clip: dict) -> dict:
    clip_filename = Path(clip["clipS3Key"]).name
    return {
        "clipId": clip["clipId"],
        "startTime": clip["startTime"],
        "endTime": clip["endTime"],
        "score": clip["score"],
        "clipUrl": build_s3_object_url(clip["s3Bucket"], clip["clipS3Key"]),
        "downloadUrl": build_s3_object_url(
            clip["s3Bucket"],
            clip["clipS3Key"],
            response_content_disposition=f'attachment; filename="{clip_filename}"',
        ),
        "thumbnailUrl": build_s3_object_url(clip["s3Bucket"], clip["thumbnailS3Key"]),
    }


def _serialize_video(video: dict) -> dict:
    return {
        **video,
        "clips": [_serialize_clip(clip) for clip in video.get("clips", [])],
    }

def _set_job_state(job_id: str, **updates) -> dict:
    with _lock:
        job = _jobs[job_id]
        job.update(updates)
        if "stage" in updates and "progress_percent" not in updates:
            job["progress_percent"] = _STAGE_PROGRESS.get(job["stage"], job.get("progress_percent", 0))
        snapshot = job.copy()

    save_job(snapshot)
    return snapshot


def _get_job(job_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(job_id)
        return job.copy() if job else None


def _remove_job(job_id: str) -> None:
    with _lock:
        _jobs.pop(job_id, None)


def _active_job_count() -> int:
    with _lock:
        return sum(1 for job in _jobs.values() if job["status"] in {"queued", "processing"})


def _cleanup_intermediate_dirs(job_id: str) -> None:
    job_dir = _job_root(job_id)
    for dirname in ("frames", "crops"):
        shutil.rmtree(job_dir / dirname, ignore_errors=True)


def _write_json(job_id: str, filename: str, payload: dict) -> None:
    output_path = _job_root(job_id) / "analysis" / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _process_job(job_id: str) -> None:
    job = _get_job(job_id)
    if job is None:
        return

    job_dir = _job_root(job_id)
    video_path = Path(job["video_path"])
    frames_dir = job_dir / "frames"
    crops_dir = job_dir / "crops"
    clips_dir = job_dir / "artifacts" / "clips"
    thumbnails_dir = job_dir / "artifacts" / "thumbnails"

    try:
        logger.info("Processing local job %s (%s)", job_id, video_path.name)
        _set_job_state(job_id, status="processing", stage="extracting_frames")
        extract_sampled_frames(video_path, frames_dir, FRAME_SAMPLE_FPS)

        _set_job_state(job_id, stage="cropping_killfeed")
        crop_killfeed_region(
            frames_dir=frames_dir,
            crops_dir=crops_dir,
            crop_x=CROP_X,
            crop_y=CROP_Y,
            crop_w=CROP_W,
            crop_h=CROP_H,
        )

        _set_job_state(job_id, stage="running_ocr")
        observations = extract_ocr_observations(crops_dir, FRAME_SAMPLE_FPS)
        analysis_request = {
            "playerName": job["player_name"],
            "observations": observations,
            "settings": {
                "fuzzyMatchThreshold": FUZZY_MATCH_THRESHOLD,
                "dedupeWindowSeconds": DEDUPE_WINDOW_SECONDS,
                "mergeWindowSeconds": MERGE_WINDOW_SECONDS,
                "clipPreSeconds": CLIP_PRE_SECONDS,
                "clipPostSeconds": CLIP_POST_SECONDS,
            },
        }
        _write_json(job_id, "analysis_request.json", analysis_request)

        _set_job_state(job_id, stage="calling_analysis_api")
        analysis_result = analyze_observations(analysis_request)
        _write_json(job_id, "analysis_result.json", analysis_result)

        _set_job_state(job_id, stage="cutting_clips")
        clips = cut_planned_clips(video_path, analysis_result.get("clipWindows", []), clips_dir)

        _set_job_state(job_id, stage="generating_thumbnails")
        clips_with_thumbnails = generate_clip_thumbnails(clips, thumbnails_dir)

        _set_job_state(job_id, stage="uploading_to_s3")
        uploaded_clips = upload_clips_and_thumbnails(job["video_id"], clips_with_thumbnails)
        replace_clips(job_id, uploaded_clips)

        clip_payload = [
            _serialize_clip(
                {
                    "clipId": clip["clip_id"],
                    "startTime": round(float(clip["start_time"]), 3),
                    "endTime": round(float(clip["end_time"]), 3),
                    "score": int(clip["score"]),
                    "s3Bucket": clip["s3_bucket"],
                    "clipS3Key": clip["clip_s3_key"],
                    "thumbnailS3Key": clip["thumbnail_s3_key"],
                }
            )
            for clip in uploaded_clips
        ]

        summary = analysis_result.get("summary", {}).copy()
        summary["clipCount"] = len(clip_payload)

        _set_job_state(
            job_id,
            status="completed",
            stage="completed",
            progress_percent=100,
            clips=clip_payload,
            summary=summary,
        )
        logger.info("Completed local job %s with %s clips", job_id, len(clip_payload))
    except Exception as exc:
        logger.exception("Local job %s failed", job_id)
        _set_job_state(
            job_id,
            status="failed",
            stage="failed",
            progress_percent=100,
            error_message=str(exc),
        )
    finally:
        final_job = _get_job(job_id)
        _cleanup_intermediate_dirs(job_id)

        if final_job and final_job["status"] == "completed":
            shutil.rmtree(job_dir, ignore_errors=True)
        elif not KEEP_JOB_ARTIFACTS:
            shutil.rmtree(job_dir, ignore_errors=True)

        _remove_job(job_id)


@app.after_request
def _add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = CORS_ALLOWED_ORIGIN
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,DELETE,OPTIONS"
    return response


@app.route("/health", methods=["GET", "OPTIONS"])
def health():
    if request.method == "OPTIONS":
        return ("", 204)
    return jsonify(
        {
            "status": "ok",
            "service": "local-helper",
            "analysisApiConfigured": True,
            "databaseConfigured": True,
            "s3Configured": True,
            "activeJobs": _active_job_count(),
        }
    )


@app.route("/jobs", methods=["POST", "OPTIONS"])
def create_job():
    if request.method == "OPTIONS":
        return ("", 204)

    if _active_job_count() >= MAX_CONCURRENT_JOBS:
        return jsonify({"error": "This demo only allows one local processing job at a time."}), 409

    upload = request.files.get("file")
    player_name = (request.form.get("playerName") or "").strip()

    if upload is None or not upload.filename:
        return jsonify({"error": "Missing required file upload."}), 400
    if not player_name:
        return jsonify({"error": "Missing required field: playerName"}), 400

    created = create_job_record(upload.filename, player_name)
    job_id = created["job_id"]
    video_id = created["video_id"]
    Path(LOCAL_TEMP_DIR).mkdir(parents=True, exist_ok=True)
    job_dir = _job_root(job_id)
    input_dir = job_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)

    safe_name = secure_filename(upload.filename) or f"{job_id}.mp4"
    video_path = input_dir / safe_name
    upload.save(video_path)

    job_state = {
        "job_id": job_id,
        "video_id": video_id,
        "status": "queued",
        "stage": "queued",
        "progress_percent": 0,
        "player_name": player_name,
        "original_filename": upload.filename,
        "video_path": str(video_path),
        "clips": [],
        "summary": None,
        "error_message": None,
    }

    with _lock:
        _jobs[job_id] = job_state

    save_job(job_state)

    thread = threading.Thread(target=_process_job, args=(job_id,), daemon=True)
    thread.start()

    return jsonify(
        {
            "jobId": job_id,
            "videoId": video_id,
            "status": "queued",
        }
    )


@app.route("/videos", methods=["GET", "DELETE", "OPTIONS"])
def get_videos():
    if request.method == "OPTIONS":
        return ("", 204)
    if request.method == "DELETE":
        if _active_job_count() > 0:
            return jsonify({"error": "Wait for the current job to finish before deleting all videos."}), 409

        clips = list_all_clips()
        for clip in clips:
            s3_client.delete_object(Bucket=clip["s3Bucket"], Key=clip["clipS3Key"])
            s3_client.delete_object(Bucket=clip["s3Bucket"], Key=clip["thumbnailS3Key"])

        deleted_count = delete_all_jobs_record()
        return jsonify({"deleted": True, "videoCount": deleted_count})

    videos = [_serialize_video(video) for video in list_jobs_with_clips()]
    return jsonify({"videos": videos})


@app.route("/videos/<video_id>/clips/<clip_id>", methods=["DELETE", "OPTIONS"])
def delete_video_clip(video_id: str, clip_id: str):
    if request.method == "OPTIONS":
        return ("", 204)

    matching = get_clips_by_ids(video_id, [clip_id])
    if not matching:
        return jsonify({"error": "Clip not found."}), 404

    clip = matching[0]
    s3_client.delete_object(Bucket=clip["s3Bucket"], Key=clip["clipS3Key"])
    s3_client.delete_object(Bucket=clip["s3Bucket"], Key=clip["thumbnailS3Key"])
    delete_clip_record(video_id, clip_id)

    return jsonify({"deleted": True, "clipId": clip_id})


@app.route("/clips/merge", methods=["POST", "OPTIONS"])
def merge_library_clips():
    if request.method == "OPTIONS":
        return ("", 204)

    payload = request.get_json(silent=True) or {}
    clip_ids = payload.get("clipIds")
    if not isinstance(clip_ids, list) or not clip_ids:
        return jsonify({"error": "Provide clipIds as a non-empty array."}), 400

    clips = get_clips_by_ids_any_video([str(clip_id) for clip_id in clip_ids])
    if len(clips) != len(clip_ids):
        return jsonify({"error": "One or more selected clips could not be found."}), 404

    merge_dir = Path(tempfile.mkdtemp(prefix="merge-library-"))
    local_paths: list[Path] = []

    try:
        for idx, clip in enumerate(clips, start=1):
            local_path = merge_dir / f"selected_{idx:03d}.mp4"
            download_video_from_s3(clip["clipS3Key"], local_path, bucket_name=clip["s3Bucket"])
            local_paths.append(local_path)

        output_path = merge_dir / "merged-library.mp4"
        if len(local_paths) == 1:
            output_path.write_bytes(local_paths[0].read_bytes())
        else:
            merge_local_clips(local_paths, output_path)

        @after_this_request
        def _cleanup_temp(response):
            shutil.rmtree(merge_dir, ignore_errors=True)
            return response

        return send_file(
            output_path,
            mimetype="video/mp4",
            as_attachment=True,
            download_name="merged-library.mp4",
        )
    except Exception:
        shutil.rmtree(merge_dir, ignore_errors=True)
        raise
