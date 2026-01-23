import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader


def setup_logging():
    settings = SettingsLoader()

    log_dir = Path(settings.get("log_dir"))
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "actions.log"
    level = settings.get("log_level", "INFO")

    logger = logging.getLogger("valutatrade")
    logger.setLevel(level)

    handler = RotatingFileHandler(
        log_file,
        maxBytes=1_000_000,   # ~1MB
        backupCount=5,
        encoding="utf-8",
    )

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
