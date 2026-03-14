import re
from pathlib import Path

_reader = None


# Purpose: Extract the numeric frame index from a sampled frame or crop filename.
# Input: frame_path (str) such as 'frame_000123.jpg'.
# Output: Integer frame index parsed from the filename.
def frame_filename_to_index(frame_path: str) -> int:
    match = re.search(r"(\d+)", Path(frame_path).stem)
    if not match:
        raise ValueError(f"Could not parse frame index from {frame_path}")
    return int(match.group(1))


# Purpose: Convert a frame index into elapsed seconds using the sample FPS.
# Input: frame_index (int) and sample_fps (float).
# Output: Float timestamp in seconds.
def frame_index_to_seconds(frame_index: int, sample_fps: float) -> float:
    if sample_fps <= 0:
        raise ValueError("sample_fps must be > 0")
    return frame_index / sample_fps


# Purpose: Lazily create and cache the EasyOCR reader the first time OCR is needed.
# Input: No arguments.
# Output: easyocr.Reader instance.
def _get_reader():
    global _reader

    if _reader is None:
        import easyocr

        # Lazy-load OCR so the worker can start without loading the model until a job actually needs it.
        _reader = easyocr.Reader(["en"], gpu=False)

    return _reader


# Purpose: Convert one EasyOCR entry into a normalized text fragment record.
# Input: entry (list) from EasyOCR containing bbox, text, and confidence.
# Output: Fragment dict or None if the OCR entry is unusable.
def _build_fragment(entry: list) -> dict | None:
    if len(entry) < 2:
        return None

    bbox = entry[0] or []
    text = str(entry[1]).strip()
    if not text or not bbox:
        return None

    try:
        xs = [float(point[0]) for point in bbox]
        ys = [float(point[1]) for point in bbox]
    except (TypeError, ValueError, IndexError):
        return None

    confidence = float(entry[2]) if len(entry) >= 3 else 0.0
    x_min = min(xs)
    x_max = max(xs)
    y_min = min(ys)
    y_max = max(ys)

    return {
        "text": text,
        "confidence": round(confidence, 4),
        "x_min": x_min,
        "x_max": x_max,
        "y_min": y_min,
        "y_max": y_max,
        "x_center": (x_min + x_max) / 2,
        "y_center": (y_min + y_max) / 2,
        "height": max(1.0, y_max - y_min),
    }


# Purpose: Group OCR fragments that appear on the same visual row.
# Input: fragments (list[dict]) from one crop image.
# Output: List of fragment rows, each sorted left-to-right.
def _group_fragments_into_rows(fragments: list[dict]) -> list[list[dict]]:
    if not fragments:
        return []

    sorted_fragments = sorted(fragments, key=lambda fragment: (fragment["y_center"], fragment["x_min"]))
    average_height = sum(fragment["height"] for fragment in sorted_fragments) / len(sorted_fragments)
    row_merge_threshold = max(12.0, average_height * 0.8)

    rows: list[dict] = []
    for fragment in sorted_fragments:
        if not rows:
            rows.append({"avg_y": fragment["y_center"], "fragments": [fragment]})
            continue

        current_row = rows[-1]
        if abs(fragment["y_center"] - current_row["avg_y"]) <= row_merge_threshold:
            current_row["fragments"].append(fragment)
            current_row["avg_y"] = sum(item["y_center"] for item in current_row["fragments"]) / len(
                current_row["fragments"]
            )
        else:
            rows.append({"avg_y": fragment["y_center"], "fragments": [fragment]})

    return [
        sorted(row["fragments"], key=lambda fragment: (fragment["x_min"], fragment["y_center"]))
        for row in rows
    ]


# Purpose: Split one OCR row into left and right sides based on the largest horizontal gap.
# Input: row_fragments (list[dict]) for a single kill-feed row.
# Output: Tuple containing left_text and right_text strings.
def _split_row_text(row_fragments: list[dict]) -> tuple[str, str]:
    if len(row_fragments) < 2:
        return "", ""

    gaps = [
        row_fragments[idx + 1]["x_min"] - row_fragments[idx]["x_max"]
        for idx in range(len(row_fragments) - 1)
    ]
    max_gap = max(gaps)
    average_height = sum(fragment["height"] for fragment in row_fragments) / len(row_fragments)
    split_threshold = max(20.0, average_height * 0.75)

    if max_gap < split_threshold:
        return "", ""

    split_at = gaps.index(max_gap) + 1
    left_text = " ".join(fragment["text"] for fragment in row_fragments[:split_at]).strip()
    right_text = " ".join(fragment["text"] for fragment in row_fragments[split_at:]).strip()
    return left_text, right_text


# Purpose: Run OCR across all crop images and return normalized observation records.
# Input: crops_dir (Path) containing crop images and sample_fps (float).
# Output: List of observation dicts for highlight analysis.
def extract_ocr_observations(crops_dir: Path, sample_fps: float) -> list[dict]:
    observations: list[dict] = []
    reader = _get_reader()

    for crop_path in sorted(crops_dir.glob("*.jpg")):
        ocr_results = reader.readtext(str(crop_path), detail=1, paragraph=False)
        fragments = [fragment for fragment in (_build_fragment(entry) for entry in ocr_results) if fragment]
        if not fragments:
            continue

        frame_idx = frame_filename_to_index(str(crop_path))
        timestamp = frame_index_to_seconds(frame_idx, sample_fps)
        for row_index, row_fragments in enumerate(_group_fragments_into_rows(fragments), start=1):
            combined_text = " ".join(fragment["text"] for fragment in row_fragments).strip()
            if not combined_text:
                continue

            left_text, right_text = _split_row_text(row_fragments)
            confidences = [fragment["confidence"] for fragment in row_fragments]

            observations.append(
                {
                    "timestamp_seconds": timestamp,
                    "frame": crop_path.name,
                    "row_index": row_index,
                    "raw_text": combined_text,
                    "left_text": left_text,
                    "right_text": right_text,
                    "ocr_confidence": round(max(confidences) if confidences else 0.0, 4),
                }
            )

    return observations
