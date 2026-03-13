from pathlib import Path
from config import settings
from config.aws import s3_client


def download_input_video(s3_key: str, job_temp_dir: Path) -> Path:
    job_temp_dir.mkdir(parents=True, exist_ok=True)
    local_video_path = job_temp_dir / "input.mov"
    s3_client.download_file(settings.AWS_S3_BUCKET, s3_key, str(local_video_path))
    return local_video_path
