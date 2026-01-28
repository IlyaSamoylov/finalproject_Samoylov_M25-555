"""
Конфигурация логирования приложения

Настраивает файловое логирование с ротацией и единым форматом для действий пользователя
с CLI и автоматического фонового обновления курсов с scheduler.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader


class SafeFormatter(logging.Formatter):
    """
    Безопасный форматтер логов. Гарантирует наличие поля trigger, обозначающее
    вызвавший логгер класс (CLI/scheduler), в записи лога.
    """
    def format(self, record):
        """
        Форматирует запись лога, подставляя значение trigger при отсутствии, иначе "-"

        Args:
            record: запись лога
        Returns:
            str: отформатированная строка лога
        """
        if not hasattr(record, "trigger"):
            record.trigger = "-"
        return super().format(record)

def setup_logging():
    """
    Инициализирует систему логирования приложения.

    Настраивает:
    - директорию логов
    - файловый лог с ротацией
    - формат рогов
    - уровень логирования из настроек

    Returns:
         logging.Logger: настроенный логер приложения
    """
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

    formatter = SafeFormatter(
        fmt="%(asctime)s %(levelname)s [%(trigger)s] %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
