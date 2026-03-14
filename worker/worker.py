from config.reader import CONFIG, require_value
from worker_api import app
from utils.logger import get_logger

LOCAL_HELPER_HOST = require_value("local_helper", "host")
LOCAL_HELPER_PORT = CONFIG.getint("local_helper", "port")

logger = get_logger("local-helper")


if __name__ == "__main__":
    logger.info(
        "Starting local helper on http://%s:%s",
        LOCAL_HELPER_HOST,
        LOCAL_HELPER_PORT,
    )
    app.run(
        host=LOCAL_HELPER_HOST,
        port=LOCAL_HELPER_PORT,
        threaded=True,
        use_reloader=False,
    )
