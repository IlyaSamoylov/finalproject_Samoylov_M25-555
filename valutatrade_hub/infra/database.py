import json
import threading
from enum import Enum
from pathlib import Path
from typing import Any

from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.infra.settings import SettingsLoader


class StorageModel(Enum):
	"""
	Типизированные идентификаторы моделей файлового хранилища.

	Используются для защиты от опечаток/валидации названий и централизованного
	управления json файлами.
	"""
	USERS = 'users'
	PORTFOLIOS = "portfolios"
	RATES = "rates"
	SESSION = "session"


class DBManager:
	"""
	Singleton абстракция над json хранилищем
	"""
	_instance = None
	_instance_lock = threading.Lock()
	_lock = threading.RLock()

	_DEFAULTS = {
		StorageModel.USERS: [],
		StorageModel.PORTFOLIOS: [],
		StorageModel.RATES: {},
		StorageModel.SESSION: {},
	}

	def __new__(cls, *args, **kwargs):
		"""
		Создание оъекта менеджера, если он еще не создан.
		"""
		if cls._instance is None:
			with cls._instance_lock:
				if cls._instance is None:
					cls._instance = super().__new__(cls)
					cls._instance._initialized = False
		return cls._instance

	def __init__(self):
		"""
		Инициализация менеджера хранилища. Создает директорию data для хранения данных и
		загружает настройки. Повторный вызов игнорируется, ибо singleton
		"""
		if getattr(self, "_initialized", False):
			return

		self._settings = SettingsLoader()
		self._data_dir = Path(self._settings.get("data_dir"))
		self._data_dir.mkdir(exist_ok=True)

		self._session_dir = self._data_dir / "session.json"

		self._initialized = True

	def build_path(self, model: StorageModel) -> Path:
		"""
		Формирует путь к файлу данных по типу модели.

		Args:
			model (StorageModel): Тип хранимых данных
		Returns:
			Path: путь к json файлу
		"""
		return self._data_dir / f"{model.value}.json"

	def _load(self, model: StorageModel):
		"""
		Загрузка данных из json хранилища. Если файл отсутствует, в зависимости от его
		модели StorageModel задается дефолтное пустое состояние

		Args:
			model (StorageModel): тип хранимых данных
		Returns:
			Any: данные из файлы
		"""
		if not isinstance(model, StorageModel):
			raise TypeError("Модель должна быть StorageModel")
		path = self.build_path(model)

		try:
			with open(path, "r", encoding="utf-8") as f:
				return json.load(f)

		except FileNotFoundError:
			default = self._DEFAULTS.get(model)
			if default is not None:
				self._atomic_save(path, default)
				return default
			raise

	def _save(self, model: StorageModel, data: Any):
		"""
		Отвалидировать, создать директорию, если нужно и сохранить данные модели
		в json файл

		Args:
			model (StorageModel): тип хранимых данных
			data (Any): данные для сохранения
		"""
		if not isinstance(model, StorageModel):
			raise TypeError("Модель должна быть StorageModel")

		path = self.build_path(model)
		path.parent.mkdir(parents=True, exist_ok=True)
		self._atomic_save(path, data)

	def _atomic_save(self, path: Path, data: Any) -> None:
		"""
		Атомарное сохранение данных через временный файл

		Args:
			path (Path): путь к файлу для сохранения
			data (Any): данные для соранения
		"""
		tmp_path = path.with_suffix(".tmp")
		with open(tmp_path, "w", encoding="utf-8") as f:
			json.dump(data, f, ensure_ascii=False, indent=4)
		tmp_path.replace(path)

	def get_user_by_username(self, username: str) -> dict | None:
		"""
		Получить пользователя по имени.

		Args:
			username (str): имя искомого пользователя
		Returns:
			dict | None: данные пользователя в словаре или None, если не найден
		"""
		users = self._load(StorageModel.USERS)
		return next((u for u in users if u["username"] == username), None)

	def get_user_by_id(self, user_id: int) -> dict | None:
		"""
		Найти пользователя по id

		Args:
			user_id (int): идентификатор искомого пользователя
		Returns:
			dict | None: данные пользователя или None, если не найден
		"""
		users = self._load(StorageModel.USERS)
		return next((u for u in users if u["user_id"] == user_id), None)

	def create_user(self, username: str, password: str) -> User:
		"""
		Создание нового пользователя и запись его в соответствующее хранилище

		Args:
			username (str): имя нового пользователя
			password (str): новый пароль нового пользователя
		Returns:
			User: объект нового пользователя
		"""
		with self._lock:
			users = self._load(StorageModel.USERS)

			if any(u["username"] == username for u in users):
				raise ValueError(f"Пользователь '{username}' уже зарегистрирован. "
									f"Войдите используя login")

			next_id = max((u["user_id"] for u in users), default=0) + 1

			user = User(next_id, username, password)
			users.append(user.to_dict())
			self._save(StorageModel.USERS, users)

			return user

	def load_portfolio(self, user: User) -> dict | None:
		"""
		Загрузить портфель пользователя

		Args:
			user (User): объект пользователя
		Returns:
			dict | None: данные портфеля пользователя или None, если портфель не найден
		"""
		portfolios = self._load(StorageModel.PORTFOLIOS)
		return next((p for p in portfolios if p["user_id"] == user.user_id), None)

	def save_portfolio(self, portfolio: Portfolio) -> None:
		"""
		Сохранить портфель пользователя.

		Args:
			portfolio (Portfolio): портфель пользователя
		"""
		with self._lock:
			portfolios = self._load(StorageModel.PORTFOLIOS)
			data = portfolio.to_dict()

			for i, p in enumerate(portfolios):
				if p["user_id"] == portfolio.user.user_id:
					portfolios[i] = data
					break
			else:
				portfolios.append(data)

			self._save(StorageModel.PORTFOLIOS, portfolios)

	def create_portfolio(self, portfolio: Portfolio) -> None:
		"""
		Создать и сохранить портфель пользователя в json хранилище

		Args:
			portfolio (Portfolio): портфель пользователя, который необходимо сохранить
		"""
		with self._lock:
			portfolios = self._load(StorageModel.PORTFOLIOS)
			if any(p["user_id"] == portfolio.user.user_id for p in portfolios):
				return
			portfolios.append(portfolio.to_dict())
			self._save(StorageModel.PORTFOLIOS, portfolios)

	def load_rates(self) -> dict:
		"""
		Загрузить из json курсы валют
		Returns:
			dict: словарь курсов валют
		"""
		return self._load(StorageModel.RATES)

	def load_session(self) -> int | None:
		"""
		Вернуть id текущего пользователя

		Returns:
			int | None: id юзера или None, если сессия пуста
		"""
		data = self._load(StorageModel.SESSION)
		return data.get("user_id")

	def save_session(self, user_id: int):
		"""
		Назначить сессионного пользователя по id

		Args:
			user_id (int): id пользователя
		"""
		with self._lock:
			self._save(StorageModel.SESSION, {"user_id": user_id})

	def clear_session(self):
		"""
		Закрыть сессию = очистить хранилище сессионнного пользователя
		"""
		with self._lock:
			self._save(StorageModel.SESSION, {})


