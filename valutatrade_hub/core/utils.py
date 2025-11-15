import json
from pathlib import Path
from typing import Any

from valutatrade_hub.constants import USERS_DIR, PORTFOLIOS_DIR, RATES_DIR, SESSION_FILE

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

def set_session(user_id: int, username: str):
	SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
	with open(SESSION_FILE, "w", encoding="utf-8") as f:
		json.dump({"user_id": user_id, "username": username}, f)

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

