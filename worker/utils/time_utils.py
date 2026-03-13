import re
from pathlib import Path


def frame_filename_to_index(frame_path: str) -> int:
    """Extract integer frame index from names like frame_000123.jpg."""
    match = re.search(r"(\d+)", Path(frame_path).stem)
    if not match:
        raise ValueError(f"Could not parse frame index from {frame_path}")
    return int(match.group(1))


def frame_index_to_seconds(frame_index: int, sample_fps: float) -> float:
    if sample_fps <= 0:
        raise ValueError("sample_fps must be > 0")
    return frame_index / sample_fps
