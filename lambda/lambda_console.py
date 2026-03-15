import json
from difflib import SequenceMatcher

## Helpers for text normalization, fuzzy matching, and event classification in the highlight analysis pipeline.

# Normalize text for matching by lowercasing and stripping non-alphanumerics.
def normalize_text(value: str) -> str:
    return "".join(ch for ch in value.lower().strip() if ch.isalnum())


# Compute a lightweight partial-ratio score between two strings for fuzzy matching
def _partial_ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0

    short, long = (a, b) if len(a) <= len(b) else (b, a)
    if short in long:
        return 100.0

    best = 0.0
    window = len(short)

    for start in range(0, len(long) - window + 1):
        candidate = long[start : start + window]
        score = SequenceMatcher(None, short, candidate).ratio() * 100.0
        if score > best:
            best = score

    return best


# Check for a username match
def is_player_match(ocr_text: str, player_name: str, threshold: int) -> tuple[bool, float]:
    norm_text = normalize_text(ocr_text)
    norm_player = normalize_text(player_name)

    if not norm_text or not norm_player:
        return False, 0.0

    if norm_player in norm_text:
        return True, 1.0

    score = _partial_ratio(norm_player, norm_text)
    return score >= threshold, round(float(score) / 100.0, 4)


def _clean_text(value) -> str:
    return str(value or "").strip()

def _combine_confidence(match_confidence: float, ocr_confidence: float) -> float:
    if ocr_confidence > 0:
        return round((match_confidence + ocr_confidence) / 2, 4)
    return round(match_confidence, 4)


# Classify one OCR observation as a player kill, death, ambiguous event, or unclassified match.
def classify_player_event(observation: dict, player_name: str, threshold: int) -> dict | None:
    raw_text = _clean_text(observation.get("raw_text"))
    left_text = _clean_text(observation.get("left_text"))
    right_text = _clean_text(observation.get("right_text"))

    if not raw_text:
        return None

    left_match, left_confidence = is_player_match(left_text, player_name, threshold)
    right_match, right_confidence = is_player_match(right_text, player_name, threshold)
    ocr_confidence = round(float(observation.get("ocr_confidence", 0.0) or 0.0), 4)

    event_type = None
    matched_side = None
    match_confidence = 0.0

    if left_match and not right_match:
        event_type = "player_kill"
        matched_side = "left"
        match_confidence = left_confidence
    elif right_match and not left_match:
        event_type = "player_death"
        matched_side = "right"
        match_confidence = right_confidence
    elif left_match and right_match:
        if left_confidence > right_confidence + 0.05:
            event_type = "player_kill"
            matched_side = "left"
            match_confidence = left_confidence
        elif right_confidence > left_confidence + 0.05:
            event_type = "player_death"
            matched_side = "right"
            match_confidence = right_confidence
        else:
            event_type = "player_related_ambiguous"
            matched_side = "both"
            match_confidence = max(left_confidence, right_confidence)
    else:
        raw_match, raw_confidence = is_player_match(raw_text, player_name, threshold)
        if not raw_match:
            return None

        event_type = "player_related_unclassified"
        matched_side = "unknown"
        match_confidence = raw_confidence

    row_index = observation.get("row_index")
    try:
        row_index = int(row_index) if row_index is not None else None
    except (TypeError, ValueError):
        row_index = None

    return {
        "timestamp_seconds": round(float(observation["timestamp_seconds"]), 3),
        "confidence": _combine_confidence(match_confidence, ocr_confidence),
        "match_confidence": round(match_confidence, 4),
        "ocr_confidence": ocr_confidence,
        "frame": observation.get("frame"),
        "row_index": row_index,
        "raw_text": raw_text,
        "left_text": left_text,
        "right_text": right_text,
        "event_type": event_type,
        "matched_side": matched_side,
    }


# Run player-event classification across all OCR observations.
# Input: observations (list[dict]), player_name (str), and threshold (int).
# Output: List of matched event dicts.
def select_matching_events(observations: list[dict], player_name: str, threshold: int) -> list[dict]:
    matched_events: list[dict] = []

    for observation in observations:
        event = classify_player_event(observation, player_name, threshold)
        if event is not None:
            matched_events.append(event)

    return matched_events


# Combine nearby repeated detections
# Input: raw_events (list[dict]) and dedupe_window_seconds (float).
# Output: List of deduped event dicts.
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


# Merge nearby events into highlight groups that should become clips.
# Input: events (list[dict]) and merge_window_seconds (float).
# Output: List of highlight-group dicts.
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


# Convert highlight groups into final clip windows and merge overlapping windows.
# Input: highlights (list[dict]), clip_pre_seconds (float), and clip_post_seconds (float).
# Output: List of clip-window dicts.
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


# Run the full highlight-analysis pipeline on one request payload.
# Input: payload (dict) containing playerName, observations, and settings.
# Output: Dict with matched events, highlight groups, clip windows, and summary counts.
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
    clip_pre_seconds = float(options.get("clipPreSeconds", 10.0))
    clip_post_seconds = float(options.get("clipPostSeconds", 0.0))

    matched_events = select_matching_events(observations, player_name, threshold)
    kill_events = [event for event in matched_events if event["event_type"] == "player_kill"]
    death_events = [event for event in matched_events if event["event_type"] == "player_death"]
    ambiguous_events = [event for event in matched_events if event["event_type"] == "player_related_ambiguous"]
    unclassified_events = [event for event in matched_events if event["event_type"] == "player_related_unclassified"]

    # Keep deaths out of final clips, but allow unclassified rows as a fallback
    # when OCR matched the player on the full row without a reliable side split.
    highlight_source_events = kill_events + unclassified_events
    deduped_events = dedupe_nearby_events(highlight_source_events, dedupe_window_seconds)
    highlights = merge_events_into_highlights(deduped_events, merge_window_seconds)
    clip_windows = build_clip_windows(highlights, clip_pre_seconds, clip_post_seconds)

    return {
        "playerName": player_name,
        "matchedEvents": matched_events,
        "killEvents": kill_events,
        "deathEvents": death_events,
        "ambiguousEvents": ambiguous_events,
        "unclassifiedEvents": unclassified_events,
        "dedupedEvents": deduped_events,
        "highlights": highlights,
        "clipWindows": clip_windows,
        "summary": {
            "observationCount": len(observations),
            "matchedCount": len(matched_events),
            "killCount": len(kill_events),
            "deathCount": len(death_events),
            "ambiguousCount": len(ambiguous_events),
            "unclassifiedCount": len(unclassified_events),
            "dedupedCount": len(deduped_events),
            "highlightCount": len(highlights),
            "clipWindowCount": len(clip_windows),
        },
    }


# Format a new Lambda/API Gateway HTTP response.
def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "OPTIONS,POST",
        },
        "body": json.dumps(body),
    }


# Purpose: Handle Lambda invocations, parse the incoming request, and return analysis results.
# Input: event from Lambda/API Gateway and context from Lambda runtime.
# Output: API Gateway proxy response dict with success or error payload.
def lambda_handler(event, context):
    try:
        print("**Call to highlight analysis")

        if event is None:
            payload = {}
        elif isinstance(event, dict) and "body" in event:
            print("**Accessing request body")
            body = event.get("body") or "{}"
            payload = json.loads(body) if isinstance(body, str) else body
        else:
            payload = event

        result = analyze_highlight_request(payload)
        print("**Responding to client")
        return _response(200, result)

    except ValueError as exc:
        print("**Client error")
        print("**Message:", str(exc))
        return _response(400, {"error": str(exc)})

    except Exception as exc:
        print("**Server error")
        print("**Message:", str(exc))
        return _response(500, {"error": str(exc)})
