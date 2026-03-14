# VOD Highlight Generator

This project has 3 parts:

- `frontend/`: React UI
- `worker/`: local Python service that processes videos
- `lambda_console.py`: AWS Lambda highlight analysis code

## Prerequisites

- Python 3
- Node.js + npm
- FFmpeg
- An S3 bucket
- A MySQL database or RDS instance
- An AWS Lambda + API Gateway endpoint for `lambda_console.py`

## Install

1. Create the database schema.

Use:

```sql
worker/schema.sql
```

2. Configure the worker.

Edit:

```ini
worker/worker-config.ini
```

Fill in:

- `[analysis_api] base_url`
- `[analysis_api] path`
- `[s3] bucket_name`
- `[s3] region_name`
- `[rds] endpoint`
- `[rds] user_name`
- `[rds] user_pwd`
- `[rds] db_name`

3. Configure the frontend.

Edit:

```ini
frontend/client-config.ini
```

Set `local_helper` to the worker URL, usually:

```ini
[client]
local_helper=http://localhost:4001
```

4. Install and start the worker.

```bash
cd worker
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python worker.py
```

5. Install and start the frontend.

```bash
cd frontend
npm install
npm run dev
```

## Lambda

Deploy `lambda_console.py` to AWS Lambda and connect it to API Gateway.

The route in API Gateway must match:

```ini
[analysis_api]
path=...
```

## Tuning Parameters

Most processing settings live in:

```ini
worker/worker-config.ini
```

Useful values to adjust:

- `frame_sample_fps`: how often frames are sampled
- `crop_x`, `crop_y`, `crop_w`, `crop_h`: kill-feed crop window
- `clip_pre_seconds`, `clip_post_seconds`: how much video to save around each event
- `dedupe_window_seconds`: how aggressively repeated OCR events are collapsed
- `merge_window_seconds`: how close events must be to merge into one highlight
- `fuzzy_match_threshold`: player-name match strictness
- `max_concurrent_jobs`: how many videos can process at once
- `temp_dir`: local working directory for worker artifacts

## Files To Edit Most Often

- `worker/worker-config.ini`
- `frontend/client-config.ini`
- `lambda_console.py`
