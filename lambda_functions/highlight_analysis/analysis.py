from rapidfuzz import fuzz


def normalize_text(value: str) -> str:
    return "".join(ch for ch in value.lower().strip() if ch.isalnum())


def is_player_match(ocr_text: str, player_name: str, threshold: int) -> tuple[bool, float]:
    norm_text = normalize_text(ocr_text)
    norm_player = normalize_text(player_name)

    if not norm_text or not norm_player:
        return False, 0.0

    if norm_player in norm_text:
        return True, 1.0

    score = fuzz.partial_ratio(norm_player, norm_text)
    return score >= threshold, round(float(score) / 100.0, 4)


def select_matching_events(observations: list[dict], player_name: str, threshold: int) -> list[dict]:
    matched_events: list[dict] = []

    for observation in observations:
        raw_text = str(observation.get("raw_text", "")).strip()
        if not raw_text:
            continue

        matched, match_confidence = is_player_match(raw_text, player_name, threshold)
        if not matched:
            continue

        ocr_confidence = float(observation.get("ocr_confidence", 0.0) or 0.0)
        combined_confidence = round(
            (match_confidence + ocr_confidence) / 2 if ocr_confidence > 0 else match_confidence,
            4,
        )

        matched_events.append(
            {
                "timestamp_seconds": round(float(observation["timestamp_seconds"]), 3),
                "confidence": combined_confidence,
                "match_confidence": match_confidence,
                "ocr_confidence": round(ocr_confidence, 4),
                "frame": observation.get("frame"),
                "raw_text": raw_text,
            }
        )

    return matched_events


def dedupe_nearby_events(raw_events: list[dict], dedupe_window_seconds: float) -> list[dict]:
    if not raw_events:
        return []

    sorted_events = sorted(raw_events, key=lambda e: e["timestamp_seconds"])
    deduped = [sorted_events[0]]

    for event in sorted_events[1:]:
        previous = deduped[-1]
        delta = event["timestamp_seconds"] - previous["timestamp_seconds"]

        if delta <= dedupe_window_seconds:
            if event["confidence"] > previous["confidence"]:
                deduped[-1] = event
        else:
            deduped.append(event)

    return deduped


def merge_events_into_highlights(events: list[dict], merge_window_seconds: float) -> list[dict]:
    if not events:
        return []

    events = sorted(events, key=lambda e: e["timestamp_seconds"])
    groups: list[list[dict]] = [[events[0]]]

    for event in events[1:]:
        if event["timestamp_seconds"] - groups[-1][-1]["timestamp_seconds"] <= merge_window_seconds:
            groups[-1].append(event)
        else:
            groups.append([event])

    highlights: list[dict] = []
    for idx, group in enumerate(groups, start=1):
        first_ts = group[0]["timestamp_seconds"]
        last_ts = group[-1]["timestamp_seconds"]
        kill_count = len(group)

        highlights.append(
            {
                "event_group_id": idx,
                "start_anchor": round(first_ts, 3),
                "end_anchor": round(last_ts, 3),
                "kill_count": kill_count,
                "score": kill_count,
                "events": group,
            }
        )

    return highlights


def build_clip_windows(highlights: list[dict], clip_pre_seconds: float, clip_post_seconds: float) -> list[dict]:
    if not highlights:
        return []

    windows = []
    for highlight in highlights:
        start_time = max(0.0, float(highlight["start_anchor"]) - clip_pre_seconds)
        end_time = max(start_time, float(highlight["end_anchor"]) + clip_post_seconds)
        windows.append(
            {
                "start_time": round(start_time, 3),
                "end_time": round(end_time, 3),
                "score": int(highlight.get("score", highlight.get("kill_count", 1))),
                "event_group_id": int(highlight["event_group_id"]),
            }
        )

    windows.sort(key=lambda window: (window["start_time"], window["end_time"]))
    merged = [windows[0].copy()]

    for window in windows[1:]:
        current = merged[-1]
        if window["start_time"] <= current["end_time"]:
            current["end_time"] = max(current["end_time"], window["end_time"])
            current["score"] += window["score"]
            continue
        merged.append(window.copy())

    return merged


def analyze_highlight_request(payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object.")

    player_name = str(payload.get("playerName", "")).strip()
    if not player_name:
        raise ValueError("Missing required field: playerName")

    observations = payload.get("observations")
    if not isinstance(observations, list):
        raise ValueError("Missing required field: observations")

    options = payload.get("settings") or {}
    threshold = int(options.get("fuzzyMatchThreshold", 78))
    dedupe_window_seconds = float(options.get("dedupeWindowSeconds", 2.0))
    merge_window_seconds = float(options.get("mergeWindowSeconds", 8.0))
    clip_pre_seconds = float(options.get("clipPreSeconds", 15.0))
    clip_post_seconds = float(options.get("clipPostSeconds", 0.0))

    matched_events = select_matching_events(observations, player_name, threshold)
    deduped_events = dedupe_nearby_events(matched_events, dedupe_window_seconds)
    highlights = merge_events_into_highlights(deduped_events, merge_window_seconds)
    clip_windows = build_clip_windows(highlights, clip_pre_seconds, clip_post_seconds)

    return {
        "playerName": player_name,
        "matchedEvents": matched_events,
        "dedupedEvents": deduped_events,
        "highlights": highlights,
        "clipWindows": clip_windows,
        "summary": {
            "observationCount": len(observations),
            "matchedCount": len(matched_events),
            "dedupedCount": len(deduped_events),
            "highlightCount": len(highlights),
            "clipWindowCount": len(clip_windows),
        },
    }
