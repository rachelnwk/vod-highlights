# VOD Highlight Generator

Class-project MVP for generating gameplay highlights with a hybrid local + AWS
pipeline.

## Current Architecture

The project now uses:

- `frontend/`: React + Vite demo UI
- `worker/`: local helper that runs on the same machine as the source video
- `lambda_functions/highlight_analysis/`: Python code intended for AWS Lambda

The source video stays local. Only compact OCR/event JSON is sent to AWS.

## End-to-End Flow

1. The frontend uploads one local video to the local helper on `localhost`.
2. The local helper extracts sampled frames and crops the fixed kill-feed region.
3. The local helper runs OCR locally and produces compact observations like
   `{timestamp_seconds, raw_text, ocr_confidence}`.
4. The local helper sends those observations to API Gateway / Lambda.
5. Lambda performs the server-side non-trivial operations:
   - OCR text normalization + fuzzy player matching
   - temporal deduplication of repeated detections
   - highlight grouping / merging
   - clip-window computation and scoring
6. Lambda returns the final clip plan as JSON.
7. The local helper cuts clips locally with `ffmpeg`, generates thumbnails, and
   serves those artifacts back to the frontend.

## Why This Version Fits The Project

- It uses AWS.
- It has a client-side app to demo the work.
- The server side consists of a web service plus another component:
  - API Gateway = web service
  - Lambda = additional server-side component
- The server side performs at least 3 distinct non-trivial operations.

This version intentionally removes the original full-video upload to S3 and the
cloud worker queue, because those were the bottlenecks and deployment pain
points for this project.

## Folder Guide

- [frontend/](/Users/rachel/Documents/cs310/final_project/frontend)
  - Browser UI for submit -> status -> clips flow.
- [worker/](/Users/rachel/Documents/cs310/final_project/worker)
  - Local helper service.
  - Runs OCR and clip cutting on the demo machine.
- [lambda_functions/highlight_analysis/](/Users/rachel/Documents/cs310/final_project/lambda_functions/highlight_analysis)
  - Python package to deploy to AWS Lambda.
  - Contains the server-side analysis logic and Lambda handler.
- [backend/](/Users/rachel/Documents/cs310/final_project/backend)
  - Legacy Node/EB files from the earlier cloud-worker design.
  - Not part of the current recommended architecture.

## Config Files

Frontend config:
- [frontend/client-config.ini](/Users/rachel/Documents/cs310/final_project/frontend/client-config.ini)

Local helper / Lambda config examples:
- [worker/highlights-config.example.ini](/Users/rachel/Documents/cs310/final_project/worker/highlights-config.example.ini)
- [backend/highlights-config.example.ini](/Users/rachel/Documents/cs310/final_project/backend/highlights-config.example.ini)

The helper reads config from any of:
- `highlights-config.ini` at the repo root
- `worker/highlights-config.ini`
- `backend/highlights-config.ini`
- `HIGHLIGHTS_CONFIG_PATH`

Typical values now are:
- `analysis_api.base_url`
- `analysis_api.path`
- `local_helper.host`
- `local_helper.port`
- `local_helper.public_base_url`
- `pipeline.frame_sample_fps`

If `analysis_api.base_url` is left blank, the local helper falls back to the
same Python analysis package locally. That is useful for development. For the
final demo, point it at your deployed API Gateway URL.

## Local Setup

### 1) Worker / Local Helper

```bash
cd worker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp highlights-config.example.ini highlights-config.ini
python worker.py
```

The local helper starts on `http://localhost:4001` by default.

### 2) Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend expects the local helper URL in:
- [frontend/client-config.ini](/Users/rachel/Documents/cs310/final_project/frontend/client-config.ini)

Default:

```ini
[client]
local_helper=http://localhost:4001
```

### 3) Lambda Deployment Folder

The Lambda code is organized in:
- [lambda_functions/highlight_analysis/handler.py](/Users/rachel/Documents/cs310/final_project/lambda_functions/highlight_analysis/handler.py)
- [lambda_functions/highlight_analysis/analysis.py](/Users/rachel/Documents/cs310/final_project/lambda_functions/highlight_analysis/analysis.py)
- [lambda_functions/highlight_analysis/requirements.txt](/Users/rachel/Documents/cs310/final_project/lambda_functions/highlight_analysis/requirements.txt)

Deploy that folder to AWS Lambda behind API Gateway, then set:

```ini
[analysis_api]
base_url=https://your-api-id.execute-api.us-east-2.amazonaws.com/prod
path=/analyze
```

## Demo Notes

- One local video at a time.
- Maximum source-video size is `300 MB`.
- Source videos never leave the local machine.
- Finished clips are served from the local helper, not S3.
- No cloud persistence is assumed in the current design.

## Legacy Files

The old Elastic Beanstalk / S3 / SQS / RDS path is still present in the repo so
you do not lose the earlier work, but it is no longer the recommended path for
this project:

- [create.bash](/Users/rachel/Documents/cs310/final_project/create.bash)
- [update.bash](/Users/rachel/Documents/cs310/final_project/update.bash)
- [delete.bash](/Users/rachel/Documents/cs310/final_project/delete.bash)
- [backend/app.js](/Users/rachel/Documents/cs310/final_project/backend/app.js)

The active path now is `frontend -> local helper -> API Gateway/Lambda -> local helper`.
