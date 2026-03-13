from pathlib import Path
from config import settings
from config.aws import s3_client


def upload_clips_and_thumbnails(video_id: int, clips: list[dict]) -> list[dict]:
    uploaded = []

    for idx, clip in enumerate(clips, start=1):
        clip_path = Path(clip["local_path"])
        thumb_path = Path(clip["thumbnail_local_path"])

        clip_key = f"clips/video-{video_id}/clip-{idx:03d}.mp4"
        thumb_key = f"thumbnails/video-{video_id}/clip-{idx:03d}.jpg"

        s3_client.upload_file(str(clip_path), settings.AWS_S3_BUCKET, clip_key)
        s3_client.upload_file(str(thumb_path), settings.AWS_S3_BUCKET, thumb_key)

        uploaded.append(
            {
                "start_time": clip["start_time"],
                "end_time": clip["end_time"],
                "score": clip["score"],
                "event_group_id": clip["event_group_id"],
                "clip_s3_key": clip_key,
                "thumbnail_s3_key": thumb_key,
            }
        )

    return uploaded
