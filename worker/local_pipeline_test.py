import argparse
import json
import shutil
import subprocess
from pathlib import Path

from config import settings
from pipeline.crop_killfeed import crop_killfeed_region
from pipeline.extract_frames import extract_sampled_frames


def run_ffprobe(video_path: Path) -> dict:
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name,width,height,avg_frame_rate",
            "-of",
            "json",
            str(video_path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def run_stage_extract(video_path: Path, job_temp_dir: Path) -> Path:
    frames_dir = job_temp_dir / "frames"
    extract_sampled_frames(video_path, frames_dir, settings.FRAME_SAMPLE_FPS)
    return frames_dir


def run_stage_crop(frames_dir: Path, job_temp_dir: Path) -> Path:
    crops_dir = job_temp_dir / "crops"
    crop_killfeed_region(
        frames_dir=frames_dir,
        crops_dir=crops_dir,
        crop_x=settings.CROP_X,
        crop_y=settings.CROP_Y,
        crop_w=settings.CROP_W,
        crop_h=settings.CROP_H,
    )
    return crops_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the worker pipeline locally against a video file.")
    parser.add_argument(
        "--video",
        default=str(Path(__file__).resolve().parents[1] / "sample.mp4"),
        help="Path to a local video file. Defaults to final_project/sample.mp4.",
    )
    parser.add_argument(
        "--job-id",
        type=int,
        default=999,
        help="Temporary local job id used to name temp output directories.",
    )
    parser.add_argument(
        "--stop-after",
        choices=["probe", "extract", "crop"],
        default="extract",
        help="Last stage to run.",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Keep temp files after the test completes.",
    )
    args = parser.parse_args()

    video_path = Path(args.video).expanduser().resolve()
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    job_temp_dir = Path(settings.LOCAL_TEMP_DIR) / f"local-test-{args.job_id}"
    if job_temp_dir.exists():
        shutil.rmtree(job_temp_dir)
    job_temp_dir.mkdir(parents=True, exist_ok=True)

    print(f"[local-test] video={video_path}")
    print(f"[local-test] temp_dir={job_temp_dir}")
    print(f"[local-test] ffmpeg={shutil.which('ffmpeg') or 'not-found'}")

    probe = run_ffprobe(video_path)
    print("[local-test] ffprobe=", json.dumps(probe, indent=2))

    if args.stop_after == "probe":
        return 0

    frames_dir = run_stage_extract(video_path, job_temp_dir)
    frame_count = len(list(frames_dir.glob("*.jpg")))
    print(f"[local-test] extracted_frames={frame_count}")

    if args.stop_after == "extract":
        if not args.keep_temp:
            shutil.rmtree(job_temp_dir, ignore_errors=True)
        return 0

    crops_dir = run_stage_crop(frames_dir, job_temp_dir)
    crop_count = len(list(crops_dir.glob("*.jpg")))
    print(f"[local-test] cropped_frames={crop_count}")

    if not args.keep_temp:
        shutil.rmtree(job_temp_dir, ignore_errors=True)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
