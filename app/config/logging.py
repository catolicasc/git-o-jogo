import logging

from app.config.settings import get_settings


def configure_logging() -> logging.Logger:
    settings = get_settings()
    level = logging.DEBUG if settings.node_env != "production" else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    return logging.getLogger("trading-agent")


logger = configure_logging()
