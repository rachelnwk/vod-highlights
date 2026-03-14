import os
from pathlib import Path

from config import constants


def _parse_ini(content: str) -> dict[str, str]:
    values: dict[str, str] = {}
    current_section: str | None = None

    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue

        if line.startswith("[") and line.endswith("]"):
            current_section = line[1:-1].strip().lower()
            continue

        equals_at = line.find("=")
        if equals_at <= 0:
            continue

        key = line[:equals_at].strip()
        value = line[equals_at + 1 :].strip()

        values[key] = value
        if current_section:
            values[f"{current_section}.{key}"] = value

    return values


def _read_ini_values() -> dict[str, str]:
    app_root = Path(__file__).resolve().parents[2]
    ini_paths = [
        app_root / "highlights-config.ini",
        app_root / "worker" / "highlights-config.ini",
        app_root / "backend" / "highlights-config.ini",
    ]

    extra_path = os.getenv("HIGHLIGHTS_CONFIG_PATH")
    if extra_path:
        resolved_path = Path(extra_path).expanduser()
        if not resolved_path.is_absolute():
            resolved_path = Path.cwd() / resolved_path
        ini_paths.append(resolved_path)

    values: dict[str, str] = {}
    for ini_path in ini_paths:
        try:
            values.update(_parse_ini(ini_path.read_text(encoding="utf-8")))
        except OSError:
            continue

    return values


_INI_VALUES = _read_ini_values()


def _first(*keys: str, default: str | None = None) -> str | None:
    for key in keys:
        env_value = os.getenv(key)
        if env_value is not None and env_value != "":
            return env_value

        ini_value = _INI_VALUES.get(key)
        if ini_value is not None and ini_value != "":
            return ini_value

    return default


def _to_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


FRAME_SAMPLE_FPS = float(
    _first("FRAME_SAMPLE_FPS", "pipeline.frame_sample_fps", default=str(constants.FRAME_SAMPLE_FPS))
)
CROP_X = int(_first("CROP_X", "pipeline.crop_x", default=str(constants.CROP_X)))
CROP_Y = int(_first("CROP_Y", "pipeline.crop_y", default=str(constants.CROP_Y)))
CROP_W = int(_first("CROP_W", "pipeline.crop_w", default=str(constants.CROP_W)))
CROP_H = int(_first("CROP_H", "pipeline.crop_h", default=str(constants.CROP_H)))

DEDUPE_WINDOW_SECONDS = float(
    _first(
        "DEDUPE_WINDOW_SECONDS",
        "pipeline.dedupe_window_seconds",
        default=str(constants.DEDUPE_WINDOW_SECONDS),
    )
)
MERGE_WINDOW_SECONDS = float(
    _first(
        "MERGE_WINDOW_SECONDS",
        "pipeline.merge_window_seconds",
        default=str(constants.MERGE_WINDOW_SECONDS),
    )
)
CLIP_PRE_SECONDS = float(
    _first("CLIP_PRE_SECONDS", "pipeline.clip_pre_seconds", default=str(constants.CLIP_PRE_SECONDS))
)
CLIP_POST_SECONDS = float(
    _first("CLIP_POST_SECONDS", "pipeline.clip_post_seconds", default=str(constants.CLIP_POST_SECONDS))
)
FUZZY_MATCH_THRESHOLD = int(
    _first(
        "FUZZY_MATCH_THRESHOLD",
        "pipeline.fuzzy_match_threshold",
        default=str(constants.FUZZY_MATCH_THRESHOLD),
    )
)

LOCAL_HELPER_HOST = _first(
    "LOCAL_HELPER_HOST",
    "local_helper.host",
    default=constants.LOCAL_HELPER_HOST,
)
LOCAL_HELPER_PORT = int(
    _first("LOCAL_HELPER_PORT", "local_helper.port", default=str(constants.LOCAL_HELPER_PORT))
)
LOCAL_HELPER_PUBLIC_BASE_URL = _first(
    "LOCAL_HELPER_PUBLIC_BASE_URL",
    "local_helper.public_base_url",
    default=constants.LOCAL_HELPER_PUBLIC_BASE_URL or f"http://localhost:{LOCAL_HELPER_PORT}",
)

ANALYSIS_API_BASE_URL = _first(
    "ANALYSIS_API_BASE_URL",
    "analysis_api.base_url",
    default=constants.ANALYSIS_API_BASE_URL,
)
ANALYSIS_API_PATH = _first(
    "ANALYSIS_API_PATH",
    "analysis_api.path",
    default=constants.ANALYSIS_API_PATH,
)
ANALYSIS_REQUEST_TIMEOUT_SECONDS = int(
    _first(
        "ANALYSIS_REQUEST_TIMEOUT_SECONDS",
        "analysis_api.timeout_seconds",
        default=str(constants.ANALYSIS_REQUEST_TIMEOUT_SECONDS),
    )
)

_max_upload_bytes = _first("MAX_UPLOAD_BYTES", "local_helper.max_upload_bytes")
if _max_upload_bytes is not None:
    MAX_UPLOAD_BYTES = int(_max_upload_bytes)
else:
    max_upload_mb = _first("MAX_UPLOAD_MB", "local_helper.max_upload_mb")
    if max_upload_mb is not None:
        MAX_UPLOAD_BYTES = int(float(max_upload_mb) * 1024 * 1024)
    else:
        MAX_UPLOAD_BYTES = int(constants.MAX_UPLOAD_BYTES)

MAX_CONCURRENT_JOBS = int(
    _first(
        "MAX_CONCURRENT_JOBS",
        "local_helper.max_concurrent_jobs",
        default=str(constants.MAX_CONCURRENT_JOBS),
    )
)
KEEP_JOB_ARTIFACTS = _to_bool(
    _first("KEEP_JOB_ARTIFACTS", "local_helper.keep_job_artifacts"),
    constants.KEEP_JOB_ARTIFACTS,
)
CORS_ALLOWED_ORIGIN = _first(
    "CORS_ALLOWED_ORIGIN",
    "local_helper.cors_allowed_origin",
    default=constants.CORS_ALLOWED_ORIGIN,
)

LOCAL_TEMP_DIR = _first("LOCAL_TEMP_DIR", "local_helper.temp_dir", default=constants.LOCAL_TEMP_DIR)
LOG_LEVEL = _first("LOG_LEVEL", default=constants.LOG_LEVEL)
