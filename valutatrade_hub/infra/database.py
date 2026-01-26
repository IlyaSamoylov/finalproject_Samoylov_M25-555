import json
import threading
from pathlib import Path
from valutatrade_hub.infra.settings import SettingsLoader
from typing import Any
from enum import Enum
from valutatrade_hub.core.models import User, Portfolio


class StorageModel(Enum):
	USERS = 'users'
	PORTFOLIOS = "portfolios"
	RATES = "rates"
	SESSION = "session"

class DBManager:
	_instance = None
	_lock = threading.Lock()

	_DEFAULTS = {
		StorageModel.USERS: [],
		StorageModel.PORTFOLIOS: [],
		StorageModel.RATES: {},
		StorageModel.SESSION: {},
	}

	def __new__(cls, *args, **kwargs):
		if cls._instance is None:
			cls._instance = super().__new__(cls)
			cls._instance._initialized = False
		return cls._instance

	def __init__(self):
		if getattr(self, "_initialized", False):
			return

		self._settings = SettingsLoader()
		self._data_dir = Path(self._settings.get("data_dir"))
		self._data_dir.mkdir(exist_ok=True)

		# self._portfolios_file = self._data_dir / "portfolios.json"
		# self._users_file = self._data_dir / "users.json"
		# self._rates_file = self._data_dir / "rates.json"
		# TODO: нужно ли мне сохранение сессии между запусками программы? Тогда оставить сессию
		self._session_dir = self._data_dir / "session.json"

		self._initialized = True

	def build_path(self, model: StorageModel) -> Path:
		return self._data_dir / f"{model.value}.json"

	def _load(self, model: StorageModel):
		if not isinstance(model, StorageModel):
			raise TypeError(f"Модель должна быть StorageModel, получил {type(model).__name__}")
		path = self.build_path(model)

		try:
			with open(path, "r", encoding="utf-8") as f:
				return json.load(f)

		except FileNotFoundError:
			if model in self._DEFAULTS:
				default = self._DEFAULTS[model]
				self._save(model, default)
				return default
			raise FileNotFoundError(f"Хранилище для {model.name} не найдено")

	def _save(self, model: StorageModel, data: Any):
		if not isinstance(model, StorageModel):
			raise TypeError(f"Модель должна быть StorageModel, получил {type(model).__name__}")

		path = self.build_path(model)
		path.parent.mkdir(parents=True, exist_ok=True)
		with open(path, "w", encoding="utf-8") as f:
			json.dump(data, f, ensure_ascii=False, indent=4)

	def load_users(self) -> list[dict]:
		return self._load(StorageModel.USERS)

	def get_user_by_username(self, username: str) -> dict | None:
		users = self.load_users()
		return next((u for u in users if u["username"] == username), None)

	def get_user_by_id(self, user_id: int) -> dict | None:
		users = self.load_users()
		return next((u for u in users if u["user_id"] == user_id), None)

	def create_user(self, username: str, password: str) -> User:
		users = self.load_users()

		if any(u["username"] == username for u in users):
			raise ValueError(f"Пользователь '{username}' уже зарегистрирован. Войдите используя login")

		next_id = max((u["user_id"] for u in users), default=0) + 1

		user = User(next_id, username, password)
		users.append(user.to_dict())
		self._save(StorageModel.USERS, users)

		return user

	def load_portfolio(self, user: User) -> dict | None:
		portfolios = self._load(StorageModel.PORTFOLIOS)
		return next((p for p in portfolios if p["user_id"] == user.user_id), None)

	def save_portfolio(self, portfolio: Portfolio) -> None:
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
		portfolios = self._load(StorageModel.PORTFOLIOS)
		if any(p["user_id"] == portfolio.user.user_id for p in portfolios):
			return
		portfolios.append(portfolio.to_dict())
		self._save(StorageModel.PORTFOLIOS, portfolios)

	def load_rates(self) -> dict:
		return self._load(StorageModel.RATES)

	def load_session(self) -> int | None:
		data = self._load(StorageModel.SESSION)
		return  data.get("user_id")

	def save_session(self, user_id: int):
		self._save(StorageModel.SESSION, {"user_id": user_id})

	def clear_session(self):
		self._save(StorageModel.SESSION, {})


