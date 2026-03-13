from pathlib import Path
from PIL import Image


def crop_killfeed_region(
    frames_dir: Path,
    crops_dir: Path,
    crop_x: int,
    crop_y: int,
    crop_w: int,
    crop_h: int,
) -> Path:
    crops_dir.mkdir(parents=True, exist_ok=True)

    # Crop-first OCR keeps signal focused on the kill feed and reduces OCR noise.
    for frame_path in sorted(frames_dir.glob("*.jpg")):
        with Image.open(frame_path) as image:
            crop = image.crop((crop_x, crop_y, crop_x + crop_w, crop_y + crop_h))
            crop.save(crops_dir / frame_path.name)

    return crops_dir
