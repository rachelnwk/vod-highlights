def dedupe_nearby_events(raw_events: list[dict], dedupe_window_seconds: float) -> list[dict]:
    if not raw_events:
        return []

    sorted_events = sorted(raw_events, key=lambda e: e["timestamp_seconds"])
    deduped = [sorted_events[0]]

    for event in sorted_events[1:]:
        previous = deduped[-1]
        delta = event["timestamp_seconds"] - previous["timestamp_seconds"]

        # Non-trivial logic: same feed text can persist over adjacent frames, so collapse repeats.
        if delta <= dedupe_window_seconds:
            if event["confidence"] > previous["confidence"]:
                deduped[-1] = event
        else:
            deduped.append(event)

    return deduped
