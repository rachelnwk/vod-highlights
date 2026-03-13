import json
import shutil
import time
from pathlib import Path

from botocore.exceptions import ClientError

from config import settings
from config.aws import sqs_client
from config.db import get_connection
from pipeline.download_video import download_input_video
from pipeline.extract_frames import extract_sampled_frames
from pipeline.crop_killfeed import crop_killfeed_region
from pipeline.ocr_detect import detect_player_events
from pipeline.dedupe_events import dedupe_nearby_events
from pipeline.merge_highlights import merge_events_into_highlights
from pipeline.cut_clips import cut_highlight_clips
from pipeline.generate_thumbnails import generate_clip_thumbnails
from pipeline.upload_outputs import upload_clips_and_thumbnails
from utils.logger import get_logger

logger = get_logger("worker")


def update_job_status(conn, job_id: int, status: str, error_message: str | None = None):
    with conn.cursor() as cur:
        if status in ("completed", "failed"):
            cur.execute(
                """
                UPDATE jobs
                SET status = %s, error_message = %s, finished_at = NOW()
                WHERE id = %s
                """,
                (status, error_message, job_id),
            )
        else:
            cur.execute(
                "UPDATE jobs SET status = %s, error_message = NULL WHERE id = %s",
                (status, job_id),
            )
    conn.commit()


def update_video_status(conn, video_id: int, status: str):
    with conn.cursor() as cur:
        cur.execute("UPDATE videos SET status = %s WHERE id = %s", (status, video_id))
    conn.commit()


def insert_events(conn, video_id: int, events: list[dict]):
    if not events:
        return

    with conn.cursor() as cur:
        for event in events:
            cur.execute(
                """
                INSERT INTO events (video_id, timestamp_seconds, confidence, event_group_id)
                VALUES (%s, %s, %s, %s)
                """,
                (
                    video_id,
                    event["timestamp_seconds"],
                    event["confidence"],
                    event.get("event_group_id"),
                ),
            )
    conn.commit()


def insert_clips(conn, video_id: int, job_id: int, uploaded_clips: list[dict]):
    if not uploaded_clips:
        return

    with conn.cursor() as cur:
        for clip in uploaded_clips:
            cur.execute(
                """
                INSERT INTO clips (
                    video_id, job_id, start_time, end_time, score, clip_s3_key, thumbnail_s3_key
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    video_id,
                    job_id,
                    clip["start_time"],
                    clip["end_time"],
                    clip["score"],
                    clip["clip_s3_key"],
                    clip["thumbnail_s3_key"],
                ),
            )
    conn.commit()


def process_job(payload: dict):
    job_id = int(payload["jobId"])
    video_id = int(payload["videoId"])
    s3_key = payload["s3Key"]
    player_name = payload["playerName"]

    logger.info("Processing job_id=%s video_id=%s", job_id, video_id)

    temp_root = Path(settings.LOCAL_TEMP_DIR)
    job_temp = temp_root / f"job-{job_id}"
    frames_dir = job_temp / "frames"
    crops_dir = job_temp / "crops"
    clips_dir = job_temp / "clips"
    thumbnails_dir = job_temp / "thumbnails"

    conn = get_connection()
    try:
        update_job_status(conn, job_id, "processing")
        update_video_status(conn, video_id, "processing")

        # Pipeline step 1: download source VOD.
        local_video_path = download_input_video(s3_key=s3_key, job_temp_dir=job_temp)

        # Pipeline step 2: extract sampled frames.
        extract_sampled_frames(local_video_path, frames_dir, settings.FRAME_SAMPLE_FPS)

        # Pipeline step 3: crop kill-feed area from each frame.
        crop_killfeed_region(
            frames_dir=frames_dir,
            crops_dir=crops_dir,
            crop_x=settings.CROP_X,
            crop_y=settings.CROP_Y,
            crop_w=settings.CROP_W,
            crop_h=settings.CROP_H,
        )

        # Pipeline step 4+5: OCR on crops and detect player-name hits.
        raw_events = detect_player_events(crops_dir, player_name, settings.FRAME_SAMPLE_FPS)

        # Pipeline step 6: dedupe repeated feed lines across nearby frames.
        deduped_events = dedupe_nearby_events(raw_events, settings.DEDUPE_WINDOW_SECONDS)

        # Pipeline step 7: merge close events and assign a simple score.
        highlights = merge_events_into_highlights(deduped_events, settings.MERGE_WINDOW_SECONDS)

        enriched_events = []
        for highlight in highlights:
            for event in highlight["events"]:
                event["event_group_id"] = highlight["event_group_id"]
                enriched_events.append(event)

        # Pipeline step 8: cut clips around highlights.
        clips = cut_highlight_clips(
            video_path=local_video_path,
            highlights=highlights,
            output_dir=clips_dir,
            clip_pre_seconds=settings.CLIP_PRE_SECONDS,
            clip_post_seconds=settings.CLIP_POST_SECONDS,
        )

        # Pipeline step 9: generate thumbnail image for each clip.
        clips_with_thumbs = generate_clip_thumbnails(clips, thumbnails_dir)

        # Pipeline step 10: upload generated assets to S3.
        uploaded_clips = upload_clips_and_thumbnails(video_id, clips_with_thumbs)

        # Pipeline step 11: persist detected events and generated clips metadata.
        insert_events(conn, video_id, enriched_events)
        insert_clips(conn, video_id, job_id, uploaded_clips)

        # Pipeline step 12: mark processing as complete.
        update_job_status(conn, job_id, "completed")
        update_video_status(conn, video_id, "completed")

        logger.info("Completed job_id=%s with %s clips", job_id, len(uploaded_clips))
    except Exception as exc:
        logger.exception("Failed job_id=%s", job_id)
        update_job_status(conn, job_id, "failed", str(exc)[:1000])
        update_video_status(conn, video_id, "failed")
        raise
    finally:
        conn.close()
        if job_temp.exists():
            shutil.rmtree(job_temp, ignore_errors=True)


def poll_forever():
    logger.info("Worker started. Polling SQS queue...")

    while True:
        try:
            response = sqs_client.receive_message(
                QueueUrl=settings.AWS_SQS_QUEUE_URL,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20,
                VisibilityTimeout=300,
            )

            messages = response.get("Messages", [])
            if not messages:
                continue

            for msg in messages:
                receipt_handle = msg["ReceiptHandle"]
                body = json.loads(msg["Body"])
                payload = body.get("payload", {})

                try:
                    process_job(payload)
                    sqs_client.delete_message(
                        QueueUrl=settings.AWS_SQS_QUEUE_URL,
                        ReceiptHandle=receipt_handle,
                    )
                except Exception:
                    # Leave message in queue for retry by visibility timeout.
                    pass

        except ClientError as err:
            logger.error("AWS client error: %s", err)
            time.sleep(5)
        except Exception as err:
            logger.error("Unexpected worker loop error: %s", err)
            time.sleep(5)


if __name__ == "__main__":
    poll_forever()
