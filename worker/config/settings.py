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
        if current_section:
            values[f"{current_section}.{key}"] = value
            if key.upper() == key:
                values[key] = value
            continue

        values[key] = value

    return values


def _read_ini_values() -> dict[str, str]:
    backend_dir = Path(__file__).resolve().parents[2] / "backend"
    ini_paths = [
        backend_dir / "highlights-config.ini",
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


def _required(name: str, *aliases: str) -> str:
    value = _first(name, *aliases)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


AWS_REGION = _required("AWS_REGION", "s3.region_name", "rds.region_name")
AWS_S3_BUCKET = _required("AWS_S3_BUCKET", "s3.bucket_name")
AWS_SQS_QUEUE_URL = _required("AWS_SQS_QUEUE_URL", "sqs.queue_url")

DB_HOST = _required("DB_HOST", "rds.endpoint")
DB_PORT = int(_first("DB_PORT", "rds.port_number", default="3306"))
DB_USER = _required("DB_USER", "rds.user_name")
DB_PASSWORD = _required("DB_PASSWORD", "rds.user_pwd")
DB_NAME = _required("DB_NAME", "rds.db_name")

FRAME_SAMPLE_FPS = float(_first("FRAME_SAMPLE_FPS", default=str(constants.FRAME_SAMPLE_FPS)))
CROP_X = int(_first("CROP_X", default=str(constants.CROP_X)))
CROP_Y = int(_first("CROP_Y", default=str(constants.CROP_Y)))
CROP_W = int(_first("CROP_W", default=str(constants.CROP_W)))
CROP_H = int(_first("CROP_H", default=str(constants.CROP_H)))

DEDUPE_WINDOW_SECONDS = float(_first("DEDUPE_WINDOW_SECONDS", default=str(constants.DEDUPE_WINDOW_SECONDS)))
MERGE_WINDOW_SECONDS = float(_first("MERGE_WINDOW_SECONDS", default=str(constants.MERGE_WINDOW_SECONDS)))
CLIP_PRE_SECONDS = float(_first("CLIP_PRE_SECONDS", default=str(constants.CLIP_PRE_SECONDS)))
CLIP_POST_SECONDS = float(_first("CLIP_POST_SECONDS", default=str(constants.CLIP_POST_SECONDS)))
FUZZY_MATCH_THRESHOLD = int(_first("FUZZY_MATCH_THRESHOLD", default=str(constants.FUZZY_MATCH_THRESHOLD)))

LOCAL_TEMP_DIR = _first("LOCAL_TEMP_DIR", default=constants.LOCAL_TEMP_DIR)
LOG_LEVEL = _first("LOG_LEVEL", default=constants.LOG_LEVEL)
