from pathlib import Path

from utils.ffmpeg_utils import run_ffmpeg


def _merge_overlapping_windows(windows: list[dict]) -> list[dict]:
	if not windows:
		return []

	sorted_windows = sorted(windows, key=lambda w: (w["start_time"], w["end_time"]))
	merged = [sorted_windows[0].copy()]

	for window in sorted_windows[1:]:
		current = merged[-1]
		if window["start_time"] <= current["end_time"]:
			current["end_time"] = max(current["end_time"], window["end_time"])
			current["score"] += window["score"]
			continue
		merged.append(window.copy())

	return merged


def cut_highlight_clips(
	video_path: Path,
	highlights: list[dict],
	output_dir: Path,
	clip_pre_seconds: float,
	clip_post_seconds: float,
) -> list[dict]:
	output_dir.mkdir(parents=True, exist_ok=True)

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

	merged_windows = _merge_overlapping_windows(windows)
	clips = []

	for idx, window in enumerate(merged_windows, start=1):
		output_path = output_dir / f"clip_{idx:03d}.mp4"
		duration = max(0.1, window["end_time"] - window["start_time"])

		command = [
			"ffmpeg",
			"-y",
			"-ss",
			str(window["start_time"]),
			"-i",
			str(video_path),
			"-t",
			str(round(duration, 3)),
			"-c:v",
			"libx264",
			"-preset",
			"veryfast",
			"-crf",
			"23",
			"-c:a",
			"aac",
			str(output_path),
		]
		run_ffmpeg(command)

		clips.append(
			{
				"event_group_id": window["event_group_id"],
				"start_time": window["start_time"],
				"end_time": window["end_time"],
				"score": window["score"],
				"local_path": output_path,
			}
		)

	return clips
