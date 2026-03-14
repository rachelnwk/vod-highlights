from config import settings
from local_helper import app
from utils.logger import get_logger

logger = get_logger("local-helper")


if __name__ == "__main__":
    logger.info(
        "Starting local helper on http://%s:%s",
        settings.LOCAL_HELPER_HOST,
        settings.LOCAL_HELPER_PORT,
    )
    app.run(
        host=settings.LOCAL_HELPER_HOST,
        port=settings.LOCAL_HELPER_PORT,
        threaded=True,
        use_reloader=False,
    )
