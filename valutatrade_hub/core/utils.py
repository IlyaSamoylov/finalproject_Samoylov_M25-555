import json
from pathlib import Path
from typing import Any

from valutatrade_hub.core.models import User
from valutatrade_hub.infra.settings import SettingsLoader

# TODO: это все перебрать, когда будет синглтон над базой данных
settings = SettingsLoader()
data_dir = Path(settings.get("data_dir"))

portfolios_dir = data_dir / "portfolios.json"
users_dir = data_dir / "users.json"
rates_dir = data_dir / "rates.json"
session_dir = data_dir / "session.json"
def load(path: Path) -> Any:
	try:
		with open(path, "r", encoding="utf-8") as f:
			return json.load(f)
	except FileNotFoundError:
		if path in [users_dir, portfolios_dir]:
			return []
		elif path == rates_dir:
			return {}
		return None

# ПЕРЕПИСЫВАЕТ ФАЙЛ
def save(path: Path, data: Any) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	with open(path, "w", encoding="utf-8") as f:
		json.dump(data, f, ensure_ascii=False, indent=4)

def set_session(user: User):
	session_dir.parent.mkdir(parents=True, exist_ok=True)
	with open(session_dir, "w", encoding="utf-8") as f:
		json.dump(user.session_info(), f, ensure_ascii=False, indent=4)

def get_session():
	if not session_dir.exists():
		return None
	with open(session_dir, "r", encoding="utf-8") as f:
		return json.load(f)

def clear_session():
	if session_dir.exists():
		session_dir.unlink()

def get_user(username: str):
	users = load(users_dir)
	for p in users:
		if p["username"] == username:
			return p
	return None

def init_data_files():
	if not users_dir.exists():
		save(users_dir, [])

	if not portfolios_dir.exists():
		save(portfolios_dir, [])

	if not rates_dir.exists():
		data = {
			"EUR_USD": {
			"rate": 1.0786,                  # 1 евро = 1.0786 доллара
			"updated_at": "2025-10-09T10:30:00"
			},
			"BTC_USD": {
			"rate": 59337.21,                # 1 биткоин = 59337.21 долларов
			"updated_at": "2025-10-09T10:29:42"
			},
			"RUB_USD": {
			"rate": 0.01016,                 # 1 рубль = 0.01016 доллара
			"updated_at": "2025-10-09T10:31:12"
			},
			"ETH_USD": {
			"rate": 3720.00,                 # 1 эфириум = 3720 долларов
			"updated_at": "2025-10-09T10:35:00"
			},
			"source": "ParserService",         # кто обновил данные (Parser Service)
			# время последнего обновления всех курсов
			"last_refresh": "2025-10-09T10:35:00"
				}
		save(rates_dir, data)

	if not session_dir.exists():
		save(session_dir, {})

