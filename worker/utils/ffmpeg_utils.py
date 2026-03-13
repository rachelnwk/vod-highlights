import subprocess


def run_ffmpeg(command: list[str]) -> None:
    """Runs an ffmpeg command and raises a clear error if the command fails."""
    process = subprocess.run(command, capture_output=True, text=True)
    if process.returncode != 0:
        raise RuntimeError(
            "FFmpeg command failed.\n"
            f"Command: {' '.join(command)}\n"
            f"Stdout: {process.stdout}\n"
            f"Stderr: {process.stderr}"
        )
