import json
from pathlib import Path
from typing import Any

from valutatrade_hub.core.models import User
from valutatrade_hub.constants import PORTFOLIOS_DIR, RATES_DIR, SESSION_FILE, USERS_DIR

def load(path: Path) -> Any:
	try:
		with open(path, "r", encoding="utf-8") as f:
			return json.load(f)
	except FileNotFoundError:
		if path in [USERS_DIR, PORTFOLIOS_DIR]:
			return []
		elif path == RATES_DIR:
			return {}
		return None

# ПЕРЕПИСЫВАЕТ ФАЙЛ
def save(path: Path, data: Any) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	with open(path, "w", encoding="utf-8") as f:
		json.dump(data, f, ensure_ascii=False, indent=4)

def set_session(user: User):
	SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
	with open(SESSION_FILE, "w", encoding="utf-8") as f:
		json.dump(user.session_info(), f, ensure_ascii=False, indent=4)

def get_session():
	if not SESSION_FILE.exists():
		return None
	with open(SESSION_FILE, "r", encoding="utf-8") as f:
		return json.load(f)

def clear_session():
	if SESSION_FILE.exists():
		SESSION_FILE.unlink()

def get_user(username: str):
	users = load(USERS_DIR)
	for p in users:
		if p["username"] == username:
			return p
	return None

def init_data_files():
	if not USERS_DIR.exists():
		save(USERS_DIR, [])

	if not PORTFOLIOS_DIR.exists():
		save(PORTFOLIOS_DIR, [])

	if not RATES_DIR.exists():
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
		save(RATES_DIR, data)

	if not SESSION_FILE.exists():
		save(SESSION_FILE, {})

