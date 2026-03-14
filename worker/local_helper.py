import json
import shutil
import threading
import uuid
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename

from analysis_client import analyze_observations
from config import settings
from pipeline.crop_killfeed import crop_killfeed_region
from pipeline.cut_clips import cut_planned_clips
from pipeline.extract_frames import extract_sampled_frames
from pipeline.generate_thumbnails import generate_clip_thumbnails
from pipeline.ocr_detect import extract_ocr_observations
from utils.logger import get_logger

logger = get_logger("local-helper")
app = Flask(__name__)

_jobs: dict[str, dict] = {}
_video_to_job: dict[str, str] = {}
_lock = threading.Lock()

_STAGE_PROGRESS = {
    "queued": 0,
    "extracting_frames": 20,
    "cropping_killfeed": 35,
    "running_ocr": 55,
    "calling_analysis_api": 72,
    "cutting_clips": 88,
    "generating_thumbnails": 96,
    "completed": 100,
    "failed": 100,
}


def _job_root(job_id: str) -> Path:
    return Path(settings.LOCAL_TEMP_DIR) / f"job-{job_id}"


def _json_path(job_id: str, filename: str) -> Path:
    return _job_root(job_id) / "analysis" / filename


def _serialize_job(job: dict) -> dict:
    return {
        "jobId": job["job_id"],
        "videoId": job["video_id"],
        "status": job["status"],
        "stage": job["stage"],
        "progressPercent": job["progress_percent"],
        "playerName": job["player_name"],
        "originalFilename": job["original_filename"],
        "errorMessage": job.get("error_message"),
        "summary": job.get("summary"),
    }


def _set_job_state(job_id: str, **updates) -> dict:
    with _lock:
        job = _jobs[job_id]
        job.update(updates)
        if "stage" in updates and "progress_percent" not in updates:
            job["progress_percent"] = _STAGE_PROGRESS.get(job["stage"], job.get("progress_percent", 0))
        return job.copy()


def _get_job(job_id: str) -> dict | None:
    with _lock:
        job = _jobs.get(job_id)
        return job.copy() if job else None


def _active_job_count() -> int:
    with _lock:
        return sum(1 for job in _jobs.values() if job["status"] in {"queued", "processing"})


def _cleanup_intermediate_dirs(job_id: str) -> None:
    job_dir = _job_root(job_id)
    for dirname in ("frames", "crops"):
        shutil.rmtree(job_dir / dirname, ignore_errors=True)


def _public_artifact_url(job_id: str, artifact_type: str, filename: str) -> str:
    return f"{settings.LOCAL_HELPER_PUBLIC_BASE_URL.rstrip('/')}/artifacts/{job_id}/{artifact_type}/{filename}"


def _write_json(job_id: str, filename: str, payload: dict) -> None:
    output_path = _json_path(job_id, filename)
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
        extract_sampled_frames(video_path, frames_dir, settings.FRAME_SAMPLE_FPS)

        _set_job_state(job_id, stage="cropping_killfeed")
        crop_killfeed_region(
            frames_dir=frames_dir,
            crops_dir=crops_dir,
            crop_x=settings.CROP_X,
            crop_y=settings.CROP_Y,
            crop_w=settings.CROP_W,
            crop_h=settings.CROP_H,
        )

        _set_job_state(job_id, stage="running_ocr")
        observations = extract_ocr_observations(crops_dir, settings.FRAME_SAMPLE_FPS)
        analysis_request = {
            "playerName": job["player_name"],
            "observations": observations,
            "settings": {
                "fuzzyMatchThreshold": settings.FUZZY_MATCH_THRESHOLD,
                "dedupeWindowSeconds": settings.DEDUPE_WINDOW_SECONDS,
                "mergeWindowSeconds": settings.MERGE_WINDOW_SECONDS,
                "clipPreSeconds": settings.CLIP_PRE_SECONDS,
                "clipPostSeconds": settings.CLIP_POST_SECONDS,
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

        clip_payload = []
        for idx, clip in enumerate(clips_with_thumbnails, start=1):
            clip_path = Path(clip["local_path"])
            thumbnail_path = Path(clip["thumbnail_local_path"])
            clip_payload.append(
                {
                    "clipId": idx,
                    "startTime": clip["start_time"],
                    "endTime": clip["end_time"],
                    "score": clip["score"],
                    "clipUrl": _public_artifact_url(job_id, "clips", clip_path.name),
                    "thumbnailUrl": _public_artifact_url(job_id, "thumbnails", thumbnail_path.name),
                }
            )

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
        _cleanup_intermediate_dirs(job_id)
        if not settings.KEEP_JOB_ARTIFACTS:
            shutil.rmtree(job_dir, ignore_errors=True)


@app.after_request
def _add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = settings.CORS_ALLOWED_ORIGIN
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response


@app.route("/health", methods=["GET", "OPTIONS"])
def health():
    if request.method == "OPTIONS":
        return ("", 204)
    return jsonify(
        {
            "status": "ok",
            "service": "local-helper",
            "analysisApiConfigured": bool(settings.ANALYSIS_API_BASE_URL),
            "activeJobs": _active_job_count(),
        }
    )


@app.route("/jobs", methods=["POST", "OPTIONS"])
def create_job():
    if request.method == "OPTIONS":
        return ("", 204)

    if _active_job_count() >= settings.MAX_CONCURRENT_JOBS:
        return jsonify({"error": "This demo only allows one local processing job at a time."}), 409

    upload = request.files.get("file")
    player_name = (request.form.get("playerName") or "").strip()

    if upload is None or not upload.filename:
        return jsonify({"error": "Missing required file upload."}), 400
    if not player_name:
        return jsonify({"error": "Missing required field: playerName"}), 400

    upload.stream.seek(0, 2)
    file_size = upload.stream.tell()
    upload.stream.seek(0)
    if file_size > settings.MAX_UPLOAD_BYTES:
        max_mb = round(settings.MAX_UPLOAD_BYTES / (1024 * 1024))
        return jsonify({"error": f"Please choose a video that is {max_mb} MB or smaller."}), 400

    job_id = uuid.uuid4().hex[:12]
    video_id = job_id
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
        _video_to_job[video_id] = job_id

    thread = threading.Thread(target=_process_job, args=(job_id,), daemon=True)
    thread.start()

    return jsonify(
        {
            "jobId": job_id,
            "videoId": video_id,
            "status": "queued",
        }
    )


@app.route("/jobs/<job_id>", methods=["GET", "OPTIONS"])
def get_job(job_id: str):
    if request.method == "OPTIONS":
        return ("", 204)

    job = _get_job(job_id)
    if job is None:
        return jsonify({"error": "Job not found."}), 404

    return jsonify(_serialize_job(job))


@app.route("/videos/<video_id>/clips", methods=["GET", "OPTIONS"])
def get_video_clips(video_id: str):
    if request.method == "OPTIONS":
        return ("", 204)

    with _lock:
        job_id = _video_to_job.get(video_id)
        job = _jobs.get(job_id) if job_id else None

    if not job:
        return jsonify({"error": "Video not found."}), 404

    return jsonify({"clips": job.get("clips", [])})


@app.route("/artifacts/<job_id>/<artifact_type>/<path:filename>", methods=["GET", "OPTIONS"])
def get_artifact(job_id: str, artifact_type: str, filename: str):
    if request.method == "OPTIONS":
        return ("", 204)

    if artifact_type not in {"clips", "thumbnails"}:
        return jsonify({"error": "Unsupported artifact type."}), 404

    directory = _job_root(job_id) / "artifacts" / artifact_type
    if not directory.exists():
        return jsonify({"error": "Artifact not found."}), 404

    return send_from_directory(directory, filename)
