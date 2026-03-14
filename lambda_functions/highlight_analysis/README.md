# Highlight Analysis Lambda

This folder contains the Python code intended for the AWS Lambda portion of the
project.

## What It Does

The Lambda receives compact OCR JSON from the local helper, then performs the
server-side highlight logic:

- normalize OCR text
- fuzzy-match OCR text against the chosen player name
- dedupe repeated nearby detections
- merge detections into highlight groups
- compute final clip windows and scores

## Files

- `analysis.py`: pure analysis logic
- `handler.py`: Lambda entry point for API Gateway
- `requirements.txt`: lightweight Lambda dependencies

## Expected Request Shape

```json
{
  "playerName": "RachelLi",
  "observations": [
    {
      "timestamp_seconds": 12.5,
      "frame": "frame_000025.jpg",
      "raw_text": "RachelLi eliminated Opponent",
      "ocr_confidence": 0.92
    }
  ],
  "settings": {
    "fuzzyMatchThreshold": 78,
    "dedupeWindowSeconds": 2.0,
    "mergeWindowSeconds": 8.0,
    "clipPreSeconds": 15.0,
    "clipPostSeconds": 0.0
  }
}
```

## Local Smoke Test

If `analysis_api.base_url` is left blank in the helper config, the local helper
imports this same analysis package directly. That makes it easy to test the new
pipeline locally before wiring the folder into AWS Lambda and API Gateway.
