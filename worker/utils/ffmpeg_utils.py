import shutil
import subprocess

from imageio_ffmpeg import get_ffmpeg_exe


# Resolve the FFmpeg executable path from PATH or the bundled imageio copy.
def get_ffmpeg_binary() -> str:
    return shutil.which("ffmpeg") or get_ffmpeg_exe()


# Run an FFmpeg command and raise a readable error if it fails.
def run_ffmpeg(command: list[str]) -> None:
    """Runs an ffmpeg command and raises a clear error if the command fails."""
    resolved_command = command.copy()
    if resolved_command and resolved_command[0] == "ffmpeg":
        resolved_command[0] = get_ffmpeg_binary()

    process = subprocess.run(resolved_command, capture_output=True, text=True)
    if process.returncode != 0:
        raise RuntimeError(
            "FFmpeg command failed.\n"
            f"Command: {' '.join(resolved_command)}\n"
            f"Stdout: {process.stdout}\n"
            f"Stderr: {process.stderr}"
        )
