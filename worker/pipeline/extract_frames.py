from pathlib import Path
from utils.ffmpeg_utils import run_ffmpeg


def extract_sampled_frames(video_path: Path, frames_dir: Path, sample_fps: float) -> Path:
    frames_dir.mkdir(parents=True, exist_ok=True)
    output_pattern = frames_dir / "frame_%06d.jpg"

    # Non-trivial server op: media transformation from video to sampled images.
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
