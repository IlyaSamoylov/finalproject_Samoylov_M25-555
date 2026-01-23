from pathlib import Path
from typing import Dict, Any
import tomli

# TODO: Приспособить SettingsLoader куда нужно
# TODO: Не забыть поставить правильную частоту обновления в pyproject.toml
class SettingsLoader:
	"""
	Singleton-класс для загрузки и предоставления конфигурации проекта.

	Ответственность:
	- загрузка конфигурации из pyproject.toml (секция [tool.valutatrade])
	- кэширование конфигурации в памяти
	- предоставление значений конфигурации через единый интерфейс
	- применение значений по умолчанию при отсутствии или ошибке загрузки

	Особенности:
	- в приложении существует ровно один экземпляр SettingsLoader
	- конфигурация загружается один раз и переиспользуется (in-memory cache)
	- reload() позволяет принудительно перечитать конфигурацию

	Класс относится к инфраструктурному слою и не содержит бизнес-логики.
	"""
	_instanse = None # Атрибут класса для хранения единственного экземпляра

	def __new__(cls, *args, **kwargs):
		"""
		Создаёт или возвращает единственный экземпляр SettingsLoader.

		Реализация Singleton через __new__ гарантирует, что при любых
		импортах и повторных вызовах будет использоваться один объект.
		"""
		# создание объекта класса
		if cls._instanse is None:
			#  создание нового экземпляра, если еще не был создан
			cls._instanse = super().__new__(cls)
			cls._instanse._initialized = False
		return cls._instanse

	def __init__(self):
		"""
		Инициализирует экземпляр SettingsLoader.

		Инициализация выполняется только один раз за жизненный цикл
		приложения. При повторных вызовах __init__ не выполняется.
		"""
		if getattr(self, "_initialized", False):
			return
		self._config : Dict[str, Any] = {}
		self._config_file = Path("pyproject.toml")

		self._load_config()
		self._initialized = True

	def _load_config(self):
		"""
		Загружает конфигурацию из файла pyproject.toml при необходимости.

		Поведение:
		- если конфигурация ещё не загружена (кэш пуст),
		  считывает данные из pyproject.toml
		- если конфигурация уже загружена, использует кэш
		- в любом случае применяет значения по умолчанию

		Метод не предназначен для принудительной перезагрузки.
		Для этого следует использовать reload().
		"""
		if self._config_file.exists() and not self._config:
			try:
				with open(self._config_file, "rb") as f:
					data = tomli.load(f)
					self._config = data.get("tool", {}).get("valutatrade", {})
			# TODO: затем заменить на логирование?
			except Exception as e:
				print(f"Ошибка загрузки конфигурации из pyproject.toml: {e}")
				self._config = {}

		self.set_defaults()

	def set_defaults(self):
		"""
		Загружает конфигурацию из файла pyproject.toml при необходимости.

		Поведение:
		- если конфигурация ещё не загружена (кэш пуст),
		  считывает данные из pyproject.toml
		- если конфигурация уже загружена, использует кэш
		- в любом случае применяет значения по умолчанию

		Метод не предназначен для принудительной перезагрузки.
		Для этого следует использовать reload().
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

		:param key: имя параметра конфигурации
		:param default: значение, возвращаемое при отсутствии ключа
		:return: значение конфигурации или default
		"""

		return self._config.get(key, default)

	def reload(self) -> None:
		"""
		Принудительно перезагружает конфигурацию из файла.

		Очищает текущий кэш конфигурации и повторно загружает данные
		из pyproject.toml с последующим применением значений по умолчанию.
		"""

		self._config.clear()
		self._load_config()