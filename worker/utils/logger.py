import logging
from config.reader import require_value

LOG_LEVEL = require_value("logging", "level")


# Create or reuse a configured logger for worker modules.
# Input: name (str) identifying the logger to fetch.
# Output: logging.Logger configured with the project log level and formatter.
def get_logger(name: str = "worker") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger
