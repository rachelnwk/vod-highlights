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
                "start_anchor": first_ts,
                "end_anchor": last_ts,
                "kill_count": kill_count,
                # MVP scoring keeps ordering simple and predictable.
                "score": kill_count,
                "events": group,
            }
        )

    return highlights
