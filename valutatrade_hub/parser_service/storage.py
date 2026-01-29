import json
import threading
from pathlib import Path
from typing import Any

from valutatrade_hub.parser_service.config import ParserConfig


class RatesStorage:
	"""
	Класс для хранения курсов валют и истории обновлений курсов
	"""
	def __init__(self, config: ParserConfig):
		"""
		Инициализирует хранилище курсов.

		Args:
			config (ParserConfig): конфигурация парсера
		"""
		self._rates_path = Path(config.RATES_FILE_PATH)
		self._history_path = Path(config.HISTORY_FILE_PATH)
		self._lock = threading.RLock()

	def save_rates(self, data: dict[str, Any]) -> None:
		"""
		Сохраняет актуальные курсы валют в файл

		Args:
			data (dict[str, Any]): cловарь с курсами и метаданными
		"""
		with self._lock:
			self._rates_path.parent.mkdir(parents=True, exist_ok=True)
			self._atomic_write(self._rates_path, data)

	def load_rates(self) -> dict[str, Any]:
		"""
		Загружает последние сохраненные курсы валют из файла

		Returns:
			Словарь с загруженными курсами, либо, если файла нет - пустую структуру
		"""
		with self._lock:
			if not self._rates_path.exists():
				return {"pairs": {}, "last_refresh": None}

			with open(self._rates_path, "r", encoding="utf-8") as f:
				return json.load(f)

	def append_history(self, records: list[dict[str, object]]) -> None:
		"""
		Добавляет записи в историю обновлений курсов.

		Args:
			records (list[dict[str, object]]): обновленная история с последними
			значениями курсов
		"""
		with self._lock:
			self._history_path.parent.mkdir(parents=True, exist_ok=True)

			if self._history_path.exists():
				try:
					with open(self._history_path, "r", encoding="utf-8") as f:
						history = json.load(f)
					if not isinstance(history, list):
						history = []
				except (json.JSONDecodeError, OSError):
					history = []
			else:
				history = []

			history.extend(records)
			self._atomic_write(self._history_path, history)

	def _atomic_write(self, path: Path, data: Any) -> None:
		"""
		Атомарная запись в json. Запись через временный файл с заменой для
		предотвращения повреждения данных при сбоях

		Args:
			path (Path): путь к целевому файлу
			data (Any): данные на запись
		"""
		tmp = path.with_suffix(".tmp")
		with open(tmp, "w", encoding="utf-8") as f:
			json.dump(data, f, ensure_ascii=False, indent=2)
		tmp.replace(path)