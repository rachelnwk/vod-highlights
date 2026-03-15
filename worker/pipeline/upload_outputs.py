from pathlib import Path

from config.aws import s3_client
from config.reader import optional_value, require_value

AWS_S3_PREFIX = optional_value("s3", "prefix", "")
AWS_S3_BUCKET = require_value("s3", "bucket_name")


# Build the S3 prefix used for all artifacts belonging to one video/job.
def _video_prefix(video_id: str) -> str:
    prefix = AWS_S3_PREFIX.strip("/")
    if prefix:
        return f"{prefix}/videos/{video_id}"
    return f"videos/{video_id}"


# Upload finalized clips and thumbnails to S3 and return their stored metadata.
# Input: video_id (str) and clips (list[dict]) with local clip and thumbnail paths.
# Output: List of uploaded clip metadata dicts ready to persist in the database.
def upload_clips_and_thumbnails(video_id: str, clips: list[dict]) -> list[dict]:
    uploaded = []
    prefix = _video_prefix(video_id)

    for idx, clip in enumerate(clips, start=1):
        clip_path = Path(clip["local_path"])
        thumb_path = Path(clip["thumbnail_local_path"])
        clip_id = f"{video_id}-clip-{idx:03d}"

        clip_key = f"{prefix}/clips/clip_{idx:03d}.mp4"
        thumb_key = f"{prefix}/thumbnails/clip_{idx:03d}.jpg"

        s3_client.upload_file(
            str(clip_path),
            AWS_S3_BUCKET,
            clip_key,
            ExtraArgs={"ContentType": "video/mp4"},
        )
        s3_client.upload_file(
            str(thumb_path),
            AWS_S3_BUCKET,
            thumb_key,
            ExtraArgs={"ContentType": "image/jpeg"},
        )

        uploaded.append(
            {
                "clip_id": clip_id,
                "clip_index": idx,
                "start_time": clip["start_time"],
                "end_time": clip["end_time"],
                "score": clip["score"],
                "s3_bucket": AWS_S3_BUCKET,
                "event_group_id": clip["event_group_id"],
                "clip_s3_key": clip_key,
                "thumbnail_s3_key": thumb_key,
            }
        )

    return uploaded
