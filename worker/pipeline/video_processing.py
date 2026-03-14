from pathlib import Path

from PIL import Image

from config.aws import s3_client
from config.reader import require_value
from utils.ffmpeg_utils import run_ffmpeg

AWS_S3_BUCKET = require_value("s3", "bucket_name")


def extract_sampled_frames(video_path: Path, frames_dir: Path, sample_fps: float) -> Path:
    frames_dir.mkdir(parents=True, exist_ok=True)
    output_pattern = frames_dir / "frame_%06d.jpg"

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-vf",
        f"fps={sample_fps}",
        str(output_pattern),
    ]
    run_ffmpeg(command)
    return frames_dir


def crop_killfeed_region(
    frames_dir: Path,
    crops_dir: Path,
    crop_x: int,
    crop_y: int,
    crop_w: int,
    crop_h: int,
) -> Path:
    crops_dir.mkdir(parents=True, exist_ok=True)

    # Crop-first OCR keeps signal focused on the kill feed and reduces OCR noise.
    for frame_path in sorted(frames_dir.glob("*.jpg")):
        with Image.open(frame_path) as image:
            crop = image.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))
            crop.save(crops_dir / frame_path.name)

    return crops_dir


def _cut_clip(video_path: Path, window: dict, output_path: Path) -> dict:
    duration = max(0.1, float(window["end_time"]) - float(window["start_time"]))

    command = [
        "ffmpeg",
        "-y",
        "-ss",
        str(window["start_time"]),
        "-i",
        str(video_path),
        "-t",
        str(round(duration, 3)),
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        str(output_path),
    ]
    run_ffmpeg(command)

    return {
        "event_group_id": int(window.get("event_group_id", 0)),
        "start_time": round(float(window["start_time"]), 3),
        "end_time": round(float(window["end_time"]), 3),
        "score": int(window.get("score", 1)),
        "local_path": output_path,
    }


def cut_planned_clips(video_path: Path, clip_windows: list[dict], output_dir: Path) -> list[dict]:
    output_dir.mkdir(parents=True, exist_ok=True)

    clips = []
    for idx, window in enumerate(sorted(clip_windows, key=lambda w: (w["start_time"], w["end_time"])), start=1):
        output_path = output_dir / f"clip_{idx:03d}.mp4"
        clips.append(_cut_clip(video_path, window, output_path))

    return clips


def generate_clip_thumbnails(clips: list[dict], thumbnails_dir: Path) -> list[dict]:
    thumbnails_dir.mkdir(parents=True, exist_ok=True)

    for clip in clips:
        clip_path = Path(clip["local_path"])
        thumb_path = thumbnails_dir / f"{clip_path.stem}.jpg"

        # Extract first-second thumbnail for quick UI preview.
        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(clip_path),
            "-ss",
            "00:00:01",
            "-vframes",
            "1",
            str(thumb_path),
        ]
        run_ffmpeg(command)

        clip["thumbnail_local_path"] = thumb_path

    return clips


def _concat_manifest_line(path: Path) -> str:
    escaped = path.resolve().as_posix().replace("'", "'\\''")
    return f"file '{escaped}'"


def merge_local_clips(clip_paths: list[Path], output_path: Path) -> Path:
    if not clip_paths:
        raise ValueError("At least one clip is required to merge.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path = output_path.parent / "concat_manifest.txt"
    manifest_path.write_text(
        "\n".join(_concat_manifest_line(path) for path in clip_paths),
        encoding="utf-8",
    )

    copy_command = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(manifest_path),
        "-c",
        "copy",
        str(output_path),
    ]

    try:
        run_ffmpeg(copy_command)
    except RuntimeError:
        # Fall back to re-encoding if stream-copy concat fails for any clip combination.
        reencode_command = [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(manifest_path),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-c:a",
            "aac",
            str(output_path),
        ]
        run_ffmpeg(reencode_command)

    return output_path


def download_video_from_s3(s3_key: str, local_video_path: Path, bucket_name: str | None = None) -> Path:
    local_video_path.parent.mkdir(parents=True, exist_ok=True)
    s3_client.download_file(bucket_name or AWS_S3_BUCKET, s3_key, str(local_video_path))
    return local_video_path
