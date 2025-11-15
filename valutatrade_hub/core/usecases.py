import secrets, hashlib, datetime

from valutatrade_hub.core.utils import save, load, set_session, get_session, get_user
from valutatrade_hub.constants import USERS_DIR, PORTFOLIOS_DIR, RATES_DIR, VALUTA

# TODO: переписать в вообще все, теперь с классами(
def register(username:  str, password: str):
	users_lst = load(USERS_DIR)

	# если вернет None, то есть неизвестный путь
	if users_lst is None:
		raise ValueError("Проверь путь до user.json")
	else:
		if get_user(username) is not None:
			print(f"Имя пользователя '{username}' уже занято")
			return
		if len(password) < 4:
			print("Пароль должен быть не короче 4 символов")
			return

	user_id = (len(users_lst)) + 1
	salt = secrets.token_hex(8)
	hash_pword = hashlib.sha256(password.encode() + salt.encode()).hexdigest()
	reg_date = datetime.datetime.now(datetime.UTC).isoformat()
	new_user = {
		"user_id": user_id,
		"username": username,
		"hashed_password": hash_pword,
		"salt": salt,
		"registration_date": reg_date
	            }
	users_lst.append(new_user)
	save(USERS_DIR, users_lst)

	user_portfolio = {
		"user_id": user_id,
		"wallets": {}
	                  }

	portfolios_lst = load(PORTFOLIOS_DIR)
	portfolios_lst.append(user_portfolio)
	save(PORTFOLIOS_DIR, portfolios_lst)
	print(f"Пользователь '{username}' зарегистрирован (id={user_id}). "
	      f"Войдите: login --username {username} --password", len(password)*"*")

def login(username: str, password: str):
	users_lst = load(USERS_DIR)
	user = get_user(username)

	if user is None:
		print(f"Пользователь '{username}' не найден")
		return

	salt = user["salt"]
	hash_right_pword = user["hashed_password"]

	hash_input_pword = hashlib.sha256(password.encode() + salt.encode()).hexdigest()
	if hash_right_pword != hash_input_pword:
		print("Неверный пароль")
		return
	print(f"Вы вошли как '{username}' ")
	set_session(user["user_id"],username)


def show_portfolio(base: str | None  = 'USD'):
	if base not in VALUTA:
		print(f"Неизвестная базовая валюта '{base}'")
		return

	session = get_session()
	if not session:
		print("Сначала выполните login")
		return

	log_user_id = session["user_id"]

	portfolios = load(PORTFOLIOS_DIR)
	if portfolios is None:
		print("Проверь путь к портфелям")
		return

	# вернуть get_portfolio, если появится функция удаления user из списка, иначе они просто будут в списке по порядку
	user_portfolio = portfolios[log_user_id-1]
	# user_portfolio = get_portfolio(log_user_id)
	# user_portfolio = [port for port in portfolios if port["user_id"] == log_user_id][0]

	if not user_portfolio:
		print(f"Портфель пользователя с id = {log_user_id} не найден")
		return

	wallets = user_portfolio["wallets"]
	if not wallets:
		print("Портфель пуст")
		return

	rates = load(RATES_DIR)

	total = 0
	for currency_code, balance in wallets.items():
		balance = balance["balance"]
		rate_k = rates[f"{currency_code}_{base}"]
		balance_tr = balance*rate_k
		total += balance_tr
		print(f"- {currency_code}: {balance} -> {balance_tr}")

	print(10*'-')
	print(f"ИТОГО: {total} {base}")

def buy(currency: str, amount: float):

	session = get_session()
	if not session:
		print("Сначала выполните login")
		return

	log_id = session["user_id"]
	log_uname = session["username"]

	if currency not in VALUTA:
		print(f"Неизвестная валюта '{currency}'")
		return
	if amount <= 0:
		print("Количество валюты должен быть положительным числом")
		return
	# Если нет такого кошелька - создать
	portfolios_lst = load(PORTFOLIOS_DIR)

	# ! вернуть, если будут удаляться user
	user_portf = portfolios_lst[log_id-1]
	# user_portf = get_portfolio(log_id)

	if user_portf is None:
		print(f"Нет портфеля для пользователя '{log_uname}'")
		return

	wallets = user_portf["wallets"]
	if not currency in wallets.keys():
		wallets[currency] = {"balance": 0.0}

	wallets[currency]["balance"] += amount

	save(PORTFOLIOS_DIR, portfolios_lst)

def sell(currency:str, amount:float):
	session = get_session()
	if not session:
		print("Сначала выполните login")
		return
	if currency not in VALUTA:
		print(f"Неизвестный код валюты '{currency}'")
		return
	if amount <= 0:
		print("Количество продаваемой валюты должно быть больше 0")
		return

	portfolios_lst = load(PORTFOLIOS_DIR)
	# ! вернуть, если можно удалять пользователей
	user_portf = portfolios_lst[session["user_id"]-1]

	user_wallets = user_portf["wallets"]
	if currency not in user_wallets.keys():
		print(f"Нет кошелька для '{currency}'")
		return
	if user_wallets[currency]["balance"] < amount:
		print(f"На кошельке недостаточно средств")
		return

	# в этот момент оно меняется по ссылкам и в списке portfolio_lst!!!
	user_wallets[currency]["balance"] -= amount

	save(PORTFOLIOS_DIR, portfolios_lst)

def get_rate(from_v:str, to:str):
	if from_v not in VALUTA:
		print(f"Исходная валюта не существует")

	if to not in VALUTA:
		print(f"Итоговая валюта не существует")

	rate_dct = load(RATES_DIR)

	last_refresh_str = rate_dct["last_refresh"]
	last_refresh = datetime.datetime.fromisoformat(last_refresh_str)

	current_time = datetime.datetime.now(datetime.UTC)

	if current_time - last_refresh < datetime.timedelta(minutes=5):
		print(f"Курс {from_v}->{to}: {rate_dct[f"{from_v}_{to}"]}, (обновлен {last_refresh}")
	else:
		print("Нет данных и недоступен Parser ->")
		print(f"Курс {from_v}->{to} недоступен. Повторите позже")
