from configparser import ConfigParser
from pathlib import Path


_WORKER_ROOT = Path(__file__).resolve().parents[1]
_INI_PATH = _WORKER_ROOT / "worker-config.ini"


# Purpose: Load the worker INI file once at startup.
# Input: No arguments.
# Output: ConfigParser populated from worker-config.ini.
def _load_ini() -> ConfigParser:
    parser = ConfigParser()
    loaded = parser.read(_INI_PATH, encoding="utf-8")
    if not loaded:
        raise RuntimeError(f"Missing worker config file: {_INI_PATH}")
    return parser


CONFIG = _load_ini()


# Purpose: Read a required config value and fail fast if it is missing or blank.
# Input: section (str) and option (str) naming the INI value to read.
# Output: String containing the requested config value.
def require_value(section: str, option: str) -> str:
    if not CONFIG.has_option(section, option):
        raise RuntimeError(f"Missing required setting [{section}] {option} in worker-config.ini")

    value = CONFIG.get(section, option).strip()
    if value == "":
        raise RuntimeError(f"Missing required setting [{section}] {option} in worker-config.ini")
    return value


# Purpose: Read an optional config value with a fallback default.
# Input: section (str), option (str), and default (str) fallback value.
# Output: String containing the config value or the default.
def optional_value(section: str, option: str, default: str = "") -> str:
    if not CONFIG.has_option(section, option):
        return default
    return CONFIG.get(section, option).strip()
