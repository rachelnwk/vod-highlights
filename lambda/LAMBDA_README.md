# Highlight Analysis Lambda

The Lambda receives compact OCR JSON from the local helper, then performs the
server-side highlight logic:

- classify each kill-feed row as player kill vs player death when possible
- normalize OCR text
- fuzzy-match OCR text against the chosen player name
- dedupe repeated nearby detections
- merge detections into highlight groups
- compute final clip windows and scores


## Expected Request Shape

```json
{
  "playerName": "Player",
  "observations": [
    {
      "timestamp_seconds": 12.5,
      "frame": "frame_000025.jpg",
      "row_index": 1,
      "raw_text": "Player eliminated Opponent",
      "left_text": "Player",
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