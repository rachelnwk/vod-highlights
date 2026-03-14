# Highlight Analysis Lambda

The Lambda receives compact OCR JSON from the local helper, then performs the
server-side highlight logic:

- classify each kill-feed row as player kill vs player death when possible
- normalize OCR text
- fuzzy-match OCR text against the chosen player name
- dedupe repeated nearby detections
- merge detections into highlight groups
- compute final clip windows and scores

## Files

- `lambda/lambda_console.py`: canonical single-file Lambda implementation
- `lambda/LAMBDA_README.md`: notes for the inline Lambda setup

## Expected Request Shape

```json
{
  "playerName": "RachelLi",
  "observations": [
    {
      "timestamp_seconds": 12.5,
      "frame": "frame_000025.jpg",
      "row_index": 1,
      "raw_text": "RachelLi eliminated Opponent",
      "left_text": "RachelLi",
      "right_text": "Opponent",
      "ocr_confidence": 0.92
    }
  ],
  "settings": {
    "fuzzyMatchThreshold": 78,
    "dedupeWindowSeconds": 2.0,
    "mergeWindowSeconds": 8.0,
    "clipPreSeconds": 10.0,
    "clipPostSeconds": 0.0
  }
}
```

## Local Smoke Test

The worker now expects `analysis_api.base_url` to point at your deployed API
Gateway endpoint. This file is the Lambda implementation that API Gateway
invokes.
