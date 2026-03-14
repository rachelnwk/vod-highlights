# Cloud VOD Highlight Generator

Class-project MVP for generating FPS highlights from uploaded gameplay videos.

## Scope
- One game profile
- One fixed kill-feed crop window
- One player name per upload
- No authentication

Fixed profile used for this project:
- Input resolution: `1920x1080`
- Kill-feed crop: top-right `450x225`
- Crop coordinates: `x=1470`, `y=0`, `w=450`, `h=225`

## End-to-End Flow
1. Frontend uploads a `.mov` to S3 (via presigned URL from backend).
2. Backend creates `videos` and `jobs` rows and sends a job to SQS.
3. Worker reads SQS message and runs OCR + clip pipeline.
4. Worker uploads generated clips/thumbnails to S3 and saves metadata to MySQL.
5. Frontend polls job status and displays final clips.

## Tech Stack
- Frontend: React + Vite
- Backend: Node.js + Express
- Worker: Python
- Cloud: S3, SQS, RDS MySQL

## Non-trivial Operations
1. OCR event detection from cropped kill-feed frames.
2. Video cutting and thumbnail generation with `ffmpeg`.
3. Merge logic for overlapping event windows before clip creation.

## API Endpoints
- `GET /health`
- `GET /ping`
- `POST /vods/presign`
- `POST /vods/complete`
- `GET /jobs/:jobId`
- `GET /videos/:videoId/clips`

## Local Setup
### 1) Database
Run `backend/schema.sql` against your MySQL instance.
This single script now creates tables and one app database user.

### Backend + Worker Configuration
The backend and worker now use the normal AWS SDK credential chain:
- Local dev: use `aws sso login`, `aws configure`, or exported AWS env vars.
- Elastic Beanstalk: use the environment EC2 instance profile for IAM access to S3/SQS.

App config lives in:
- `backend/highlights-config.ini`
- starter template: `backend/highlights-config.example.ini`

Environment variables always win over `.ini` values.

Important:
- The app reads database and bucket/queue settings from the `.ini` file by default.
- Do not store AWS access keys in the `.ini`; use IAM for AWS auth.
- If you ever put this project in git, add the real `.ini` file to `.gitignore`.

For a fresh machine:
```bash
cp backend/highlights-config.example.ini backend/highlights-config.ini
```
Then fill in your real RDS, S3, and SQS values locally.

Example local setup:
```bash
export AWS_PROFILE=your-profile
```

Typical `.ini` values:
- `rds.endpoint`
- `rds.port_number`
- `rds.user_name`
- `rds.user_pwd`
- `rds.db_name`
- `s3.bucket_name`
- `s3.region_name`
- `sqs.queue_url`

### 2) Backend
```bash
cd backend
npm install
npm run dev
```

### 3) Worker (for macOS)
```bash
cd worker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python worker.py
```

### 4) Frontend
```bash
cd frontend
npm install
npm run dev
```

When testing the frontend against the deployed backend, set `frontend/client-config.ini`:
```ini
[client]
webservice=https://your-eb-env.us-east-2.elasticbeanstalk.com
```

## Elastic Beanstalk Deployment
The provided `create.bash` and `update.bash` scripts now:
- package only the backend app
- include `backend/highlights-config.ini` in the deployment bundle
- exclude `.env` files
- attach an EC2 instance profile so the backend can use IAM for S3/SQS

Before running either script:
```bash
export AWS_PROFILE=your-aws-profile
```

Optional EB variables:
```bash
export EB_INSTANCE_PROFILE=aws-elasticbeanstalk-ec2-role
export EB_SERVICE_ROLE=aws-elasticbeanstalk-service-role
```

Create a new EB environment on macOS/Linux:
```bash
./create.bash
```

Deploy an update on macOS/Linux:
```bash
./update.bash
```

Create a new EB environment on Windows PowerShell:
```powershell
.\create.ps1
```

Deploy an update on Windows PowerShell:
```powershell
.\update.ps1
```

Delete the EB environment on Windows PowerShell:
```powershell
.\delete.ps1
```

Your EB instance profile should allow at least:
- `s3:PutObject` on the uploads bucket
- `s3:ListBucket` if you want `GET /ping` to count objects
- `sqs:SendMessage` on the processing queue

## Notes
- `GET /health` is now a lightweight process check for EB and local smoke tests.
- `GET /ping` is the deeper check that touches both S3 and MySQL.
- This project is intentionally optimized for a class demo, not general-purpose production use.
- OCR quality depends on feed readability and consistent capture settings.
