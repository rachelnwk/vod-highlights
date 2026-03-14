import json
import threading

import pymysql

from config.reader import require_value
from config.db import get_connection

AWS_S3_BUCKET = require_value("s3", "bucket_name")

_SCHEMA_LOCK = threading.Lock()
_SCHEMA_READY = False


def _parse_summary(value):
    if not value:
        return None
    if isinstance(value, dict):
        return value
    return json.loads(value)


def _job_from_row(row: dict) -> dict:
    job_id = str(row["job_id"])
    return {
        "jobId": job_id,
        "videoId": job_id,
        "status": row["status"],
        "stage": row["stage"],
        "progressPercent": int(row["progress_percent"] or 0),
        "playerName": row["player_name"],
        "originalFilename": row["original_filename"],
        "errorMessage": row["error_message"],
        "summary": _parse_summary(row["summary_json"]),
        "createdAt": row["created_at"].isoformat() if row.get("created_at") else None,
        "updatedAt": row["updated_at"].isoformat() if row.get("updated_at") else None,
    }


def _clip_from_row(row: dict) -> dict:
    return {
        "clipId": str(row["clip_id"]),
        "videoId": str(row["job_id"]),
        "clipIndex": int(row["clip_index"]),
        "startTime": round(float(row["start_time"]), 3),
        "endTime": round(float(row["end_time"]), 3),
        "score": int(row["score"]),
        "s3Bucket": AWS_S3_BUCKET,
        "clipS3Key": row["clip_s3_key"],
        "thumbnailS3Key": row["thumbnail_s3_key"],
    }


def _execute(statement: str, params=None, *, fetch: str | None = None):
    ensure_schema()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(statement, params or ())

        result = None
        if fetch == "one":
            result = cursor.fetchone()
        elif fetch == "all":
            result = cursor.fetchall()

        conn.commit()
        cursor.close()
        return result
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def ensure_schema() -> None:
    global _SCHEMA_READY
    if _SCHEMA_READY:
        return

    with _SCHEMA_LOCK:
        if _SCHEMA_READY:
            return

        conn = get_connection()
        try:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT 1 FROM jobs LIMIT 0")
                cursor.execute("SELECT 1 FROM clips LIMIT 0")
            except pymysql.MySQLError as exc:
                raise RuntimeError(
                    "Database schema is missing or incomplete. "
                    f"Apply worker/schema.sql to your MySQL database. MySQL said: {exc.args[1] if len(exc.args) > 1 else str(exc)}"
                ) from exc

            cursor.close()
            _SCHEMA_READY = True
        finally:
            conn.close()


def create_job_record(original_filename: str, player_name: str) -> dict:
    ensure_schema()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO jobs (
                original_filename,
                player_name,
                status,
                stage,
                progress_percent,
                error_message
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (original_filename, player_name, "queued", "queued", 0, None),
        )
        job_id = cursor.lastrowid

        conn.commit()
        cursor.close()
        return {
            "job_id": str(job_id),
            "video_id": str(job_id),
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def save_job(job: dict) -> None:
    summary = job.get("summary")
    terminal = job["status"] in {"completed", "failed"}

    _execute(
        """
        UPDATE jobs
        SET original_filename = %s,
            player_name = %s,
            status = %s,
            stage = %s,
            progress_percent = %s,
            summary_json = %s,
            error_message = %s,
            finished_at = CASE
                WHEN %s THEN COALESCE(finished_at, CURRENT_TIMESTAMP)
                ELSE NULL
            END
        WHERE id = %s
        """,
        (
            job["original_filename"],
            job["player_name"],
            job["status"],
            job["stage"],
            int(job.get("progress_percent", 0)),
            json.dumps(summary) if summary is not None else None,
            job.get("error_message"),
            terminal,
            job["job_id"],
        ),
    )


def list_jobs_with_clips() -> list[dict]:
    job_rows = _execute(
        """
        SELECT
            id AS job_id,
            status,
            stage,
            progress_percent,
            player_name,
            original_filename,
            summary_json,
            error_message,
            created_at,
            COALESCE(finished_at, created_at) AS updated_at
        FROM jobs
        ORDER BY created_at DESC
        """,
        fetch="all",
    ) or []

    jobs = [_job_from_row(row) for row in job_rows]
    if not jobs:
        return []

    job_ids = [job["jobId"] for job in jobs]
    placeholders = ", ".join(["%s"] * len(job_ids))
    clip_rows = _execute(
        f"""
        SELECT
            id AS clip_id,
            job_id,
            clip_index,
            start_time,
            end_time,
            score,
            clip_s3_key,
            thumbnail_s3_key
        FROM clips
        WHERE job_id IN ({placeholders})
        ORDER BY job_id ASC, clip_index ASC
        """,
        tuple(job_ids),
        fetch="all",
    ) or []

    clips_by_job: dict[str, list[dict]] = {job_id: [] for job_id in job_ids}
    for row in clip_rows:
        clips_by_job.setdefault(str(row["job_id"]), []).append(_clip_from_row(row))

    for job in jobs:
        job["clips"] = clips_by_job.get(job["jobId"], [])

    return jobs


def list_all_clips() -> list[dict]:
    rows = _execute(
        """
        SELECT
            id AS clip_id,
            job_id,
            clip_index,
            start_time,
            end_time,
            score,
            clip_s3_key,
            thumbnail_s3_key
        FROM clips
        ORDER BY job_id ASC, clip_index ASC
        """,
        fetch="all",
    ) or []
    return [_clip_from_row(row) for row in rows]


def get_clips_by_ids(video_id: str, clip_ids: list[str]) -> list[dict]:
    if not clip_ids:
        return []

    placeholders = ", ".join(["%s"] * len(clip_ids))
    rows = _execute(
        f"""
        SELECT
            id AS clip_id,
            job_id,
            clip_index,
            start_time,
            end_time,
            score,
            clip_s3_key,
            thumbnail_s3_key
        FROM clips
        WHERE job_id = %s AND id IN ({placeholders})
        ORDER BY clip_index ASC
        """,
        tuple([video_id, *clip_ids]),
        fetch="all",
    ) or []

    return [_clip_from_row(row) for row in rows]


def get_clips_by_ids_any_video(clip_ids: list[str]) -> list[dict]:
    if not clip_ids:
        return []

    placeholders = ", ".join(["%s"] * len(clip_ids))
    rows = _execute(
        f"""
        SELECT
            id AS clip_id,
            job_id,
            clip_index,
            start_time,
            end_time,
            score,
            clip_s3_key,
            thumbnail_s3_key
        FROM clips
        WHERE id IN ({placeholders})
        """,
        tuple(clip_ids),
        fetch="all",
    ) or []

    clips_by_id = {
        clip["clipId"]: clip
        for clip in (_clip_from_row(row) for row in rows)
    }

    ordered = []
    seen = set()
    for clip_id in clip_ids:
        clip = clips_by_id.get(str(clip_id))
        if clip is None or clip["clipId"] in seen:
            continue
        ordered.append(clip)
        seen.add(clip["clipId"])

    return ordered


def replace_clips(job_id: str, clips: list[dict]) -> None:
    ensure_schema()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM clips WHERE job_id = %s", (job_id,))
        if clips:
            cursor.executemany(
                """
                INSERT INTO clips (
                    job_id,
                    clip_index,
                    start_time,
                    end_time,
                    score,
                    clip_s3_key,
                    thumbnail_s3_key
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    (
                        job_id,
                        int(clip["clip_index"]),
                        float(clip["start_time"]),
                        float(clip["end_time"]),
                        int(clip["score"]),
                        clip["clip_s3_key"],
                        clip["thumbnail_s3_key"],
                    )
                    for clip in clips
                ],
            )
        conn.commit()
        cursor.close()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_clip(video_id: str, clip_id: str) -> dict | None:
    ensure_schema()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                id AS clip_id,
                job_id,
                clip_index,
                start_time,
                end_time,
                score,
                clip_s3_key,
                thumbnail_s3_key
            FROM clips
            WHERE job_id = %s AND id = %s
            """,
            (video_id, clip_id),
        )
        row = cursor.fetchone()
        if row is None:
            conn.commit()
            cursor.close()
            return None

        cursor.execute(
            "DELETE FROM clips WHERE job_id = %s AND id = %s",
            (video_id, clip_id),
        )
        conn.commit()
        cursor.close()
        return _clip_from_row(row)
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_all_jobs() -> int:
    ensure_schema()
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) AS job_count FROM jobs")
        deleted_count = int((cursor.fetchone() or {}).get("job_count", 0))

        cursor.execute("DELETE FROM clips")
        cursor.execute("DELETE FROM jobs")
        cursor.execute("ALTER TABLE clips AUTO_INCREMENT = 1")
        cursor.execute("ALTER TABLE jobs AUTO_INCREMENT = 1")

        conn.commit()
        cursor.close()
        return deleted_count
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
