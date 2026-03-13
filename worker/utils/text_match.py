import re
from rapidfuzz import fuzz


def normalize_text(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9]+", "", value)
    return value


def is_player_match(ocr_text: str, player_name: str, threshold: int) -> tuple[bool, float]:
    """Returns (is_match, confidence_score) using exact and fuzzy checks."""
    norm_text = normalize_text(ocr_text)
    norm_player = normalize_text(player_name)

    if not norm_text or not norm_player:
        return False, 0.0

    if norm_player in norm_text:
        return True, 1.0

    score = fuzz.partial_ratio(norm_player, norm_text)
    return score >= threshold, float(score) / 100.0
