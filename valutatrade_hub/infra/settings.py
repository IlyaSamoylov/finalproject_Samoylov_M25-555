import logging
import threading
from pathlib import Path
from typing import Any, Dict

import tomli

logger = logging.getLogger("valutatrade")

class SettingsLoader:
	"""
	Singleton-класс для загрузки и предоставления конфигурации приложения.

	Читает параметры из pyproject.toml, заполняет пропущенные дефолтными значениями,
	кэширует их в памяти и предоставляет доступ	через единый интерфейс.
	"""
	_instance = None
	_instance_lock = threading.Lock()
	_lock = threading.RLock()

	def __new__(cls, *args, **kwargs):
		"""
		Создаёт или возвращает единственный экземпляр SettingsLoader.

		Реализация Singleton через __new__ гарантирует, что при любых
		импортах и повторных вызовах будет использоваться один объект.
		"""
		if cls._instance is None:
			with cls._instance_lock:
				if cls._instance is None:
					cls._instance = super().__new__(cls)
					cls._instance._initialized = False
		return cls._instance

	def __init__(self):
		"""
		Инициализирует конфигурацию при первом создании экземпляра.

		Инициализация выполняется только один раз за жизненный цикл
		приложения. При повторных вызовах __init__ не выполняется.
		"""
		if getattr(self, "_initialized", False):
			return
		self._config: Dict[str, Any] = {}
		self._config_file = Path("pyproject.toml")
		with self._lock:
			self._load_config()
		self._initialized = True

	def _load_config(self):
		"""
		Загружает конфигурацию из файла pyproject.toml и при необходимости заполняет
		пустоты значениями по умолчанию
		"""
		if self._config_file.exists() and not self._config:
			try:
				with open(self._config_file, "rb") as f:
					data = tomli.load(f)
					self._config = data.get("tool", {}).get("valutatrade", {})
			except Exception as e:
				logger.warning("Ошибка загрузки конфигурации из pyproject.toml: %s",
								e)
				self._config = {}

		self._set_defaults()

	def _set_defaults(self):
		"""
		Применяет значения конфигурации по умолчанию для отсутствующих ключей.
		"""
		defaults = {
			"data_dir": "data",
			"log_dir": "logs",
			"log_level": "INFO",
			"log_format": "json",
			"default_base_currency": "USD",
			"rates_ttl_seconds": 300
		}

		# объединить defaults с тем, что все таки удалось стянуть из .toml
		for key, value in defaults.items():
			if key not in self._config:
				self._config[key] = value

	def get(self, key: str, default: Any = None) -> Any:
		"""
		Возвращает значение конфигурации по ключу.

		Args:
			key (str): название параметра конфигурации
			default: дефолтное значение, возвращаемое при отсутствии ключа
		Returns:
			значение конфигурации или default
		"""
		with self._lock:
			return self._config.get(key, default)

	def reload(self) -> None:
		"""
		Принудительно перезагружает конфигурацию из файла.
		"""
		with self._lock:
			self._config.clear()
			self._load_config()