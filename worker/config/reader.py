from configparser import ConfigParser
from pathlib import Path

_WORKER_ROOT = Path(__file__).resolve().parents[1]
_INI_PATH = _WORKER_ROOT / "worker-config.ini"

def _load_ini() -> ConfigParser:
    parser = ConfigParser()
    loaded = parser.read(_INI_PATH, encoding="utf-8")
    if not loaded:
        raise RuntimeError(f"Missing worker config file: {_INI_PATH}")
    return parser

CONFIG = _load_ini()

#
# Reader functions for config values
#

# REQUIRED
def require_value(section: str, option: str) -> str:
    if not CONFIG.has_option(section, option):
        raise RuntimeError(f"Missing required setting [{section}] {option} in worker-config.ini")

    value = CONFIG.get(section, option).strip()
    if value == "":
        raise RuntimeError(f"Missing required setting [{section}] {option} in worker-config.ini")
    return value

# OPTIONAL
def optional_value(section: str, option: str, default: str = "") -> str:
    if not CONFIG.has_option(section, option):
        return default
    return CONFIG.get(section, option).strip()
