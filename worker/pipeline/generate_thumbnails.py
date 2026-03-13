from pathlib import Path
from utils.ffmpeg_utils import run_ffmpeg


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
