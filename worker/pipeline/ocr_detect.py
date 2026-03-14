import os
from pathlib import Path

from utils.text_match import is_player_match
from utils.time_utils import frame_filename_to_index, frame_index_to_seconds

_reader = None


def _get_reader():
    global _reader

    if _reader is None:
        import easyocr

        # Lazy-load OCR so the worker can start without loading the model until a job actually needs it.
        _reader = easyocr.Reader(["en"], gpu=False)

    return _reader


def detect_player_events(
    crops_dir: Path,
    player_name: str,
    sample_fps: float,
    fuzzy_match_threshold: int | None = None,
) -> list[dict]:
    detections: list[dict] = []
    threshold = fuzzy_match_threshold if fuzzy_match_threshold is not None else int(os.getenv("FUZZY_MATCH_THRESHOLD", "78"))
    reader = _get_reader()

    for crop_path in sorted(crops_dir.glob("*.jpg")):
        ocr_results = reader.readtext(str(crop_path), detail=1, paragraph=False)
        combined_text = " ".join([entry[1] for entry in ocr_results])

        matched, confidence = is_player_match(
            ocr_text=combined_text,
            player_name=player_name,
            threshold=threshold,
        )

        if matched:
            frame_idx = frame_filename_to_index(str(crop_path))
            timestamp = frame_index_to_seconds(frame_idx, sample_fps)
            detections.append(
                {
                    "timestamp_seconds": timestamp,
                    "confidence": confidence,
                    "frame": crop_path.name,
                    "raw_text": combined_text,
                }
            )

    return detections
