import datetime
import hashlib

from valutatrade_hub.constants import PORTFOLIOS_DIR, RATES_DIR, USERS_DIR
import json

# TODO: ОКАЗЫВАЕТСЯ, КЛАССЫ ВООБЩЕ НЕ ТРОГАЮТ JSON И НАОБОРОТ!!!
class User:
	# todo: убедиться, что User будут передаваться правильные форматы date/password
	def __init__(self, user_id: int, username: str, hashed_password: str,
	             salt: str, registration_date: datetime.datetime):

		# валидация username
		if not isinstance(username, str) or not username.strip():
			raise ValueError("Имя не может быть пустым")
		# минимальная проверка hashed_password (хеш — строка, не пустая)
		if not isinstance(hashed_password, str) or not hashed_password:
			raise ValueError("Неверный формат hashed_password")

		self._user_id = user_id
		self._username = username
		self._hashed_password = hashed_password
		self._salt = salt
		self._registration_date = registration_date
	@property
	def user_id(self):
		return self._user_id

	@property
	def username(self):
		return self._username

	@username.setter
	def username(self, value: str):
		if not value:
			raise ValueError("Имя не может быть пустым")
		self._username = value

	@property
	def hashed_password(self):
		return self._hashed_password

	@property
	def salt(self):
		return self._salt

	@property
	def registration_date(self):
		return self._registration_date

	def get_user_info(self):
		return {
			"User ID": self.user_id,
			"Username": self.username,
			"Registration Date": self.registration_date
		}

	def change_password(self, new_password: str):
		if len(new_password) < 4:
			raise ValueError("Пароль должен содержать хотя бы 4 символа")
		self._hashed_password = self._hash(new_password)

	def verify_password(self, password: str):
		return self._hash(password) == self._hashed_password

	def _hash(self, password: str) -> str:
		return hashlib.sha256(password.encode() + self._salt.encode()).hexdigest()

class Wallet:
	def __init__(self, currency_code: str, _balance: float):
		self.currency_code = currency_code
		self._balance = _balance

	def deposit(self, amount:float):
		if not isinstance(amount, (int, float)):
			raise ValueError("'Количество' денег должно быть числом")
		if amount < 0:
			raise ValueError("Нельзя положить отрицательное количество денег")

		self._balance += amount

	def withdraw(self, amount:float):
		if amount <= 0:
			raise ValueError("Сумма снятие не может быть меньше или равна 0")
		if amount > self.balance:
			raise ValueError("Сумма снятия не может превышать баланс")
		self._balance -= amount

	def get_balance_info(self):
		return {
			"Currency code": self.currency_code,
			"Balance": self._balance
		}

	@property
	def balance(self):
		return self._balance

	@balance.setter
	def balance(self, value: float):
		if value < 0:
			raise ValueError("Баланс не может быть меньше 0")
		if not isinstance(value, (int, float)):
			raise ValueError("Некорректный тип данных")
		self._balance = value

class Portfolio:
	def __init__(self, user_id: int, _wallets: dict[str, Wallet]):
		self._user_id = user_id
		self._wallets = _wallets

	def add_currency(self, currency_code: str):
		if currency_code in self._wallets.keys():
			raise ValueError("Такой кошелек в портфеле уже есть")
		self._wallets[currency_code] = Wallet(currency_code, 0)

	def get_total_value(self, base_currency: str ='USD'):
		try:
			with open(PORTFOLIOS_DIR, "r") as f:
				portfolios_list = json.load(f)
				user_portf = [port for port in portfolios_list if port["user_id"]
				              == self._user_id]
		except FileNotFoundError:
			print("Файл с данными о портфелях не существует")

		try:
			with open(RATES_DIR, "r") as f:
				rates_dict = json.load(f)
		except FileNotFoundError:
			print("Файл с данными о курсах валют не существует")

		if not user_portf:
			print("Пользователь с таким id не отслеживается")
			return 0

		total = 0

		for valuta, balance_info in user_portf[0]["wallets"].items():
			total += balance_info["balance"] * rates_dict[valuta][base_currency]

		return total

	def get_wallet(self, currency_code):
		# сначала проверяем в памяти
		w = self._wallets.get(currency_code)
		if w:
			return w

		# попытка подгрузить из файла portfolios.json
		try:
			with open(PORTFOLIOS_DIR, "r", encoding="utf-8") as f:
				portfolios = json.load(f)
		except FileNotFoundError:
			raise FileNotFoundError("Файл portfolios.json не найден")

		portfolio = next((p for p in portfolios if p.get("user_id") == self._user_id),
		                 None)
		if not portfolio:
			raise ValueError(
				"Портфель для пользователя с id={} не найден".format(self._user_id))

		wallets_dict = portfolio.get("wallets", {})
		w_data = wallets_dict.get(currency_code)
		if not w_data:
			raise ValueError("Кошелёк с кодом {} не найден".format(currency_code))

		wallet_obj = Wallet(currency_code=w_data.get("currency_code", currency_code),
		                    _balance=float(w_data["balance"]))
		# кэшируем в self._wallets
		self._wallets[currency_code] = wallet_obj
		return wallet_obj

	@property
	def user(self):
		try:
			with open(USERS_DIR, "r") as f:
				users_dict = json.load(f)
			user_list = [user for user in users_dict if user["user_id"] == self._user_id]

		except FileNotFoundError:
			print("Файл с данными пользователей не найден")

		if not user_list:
			print("Пользователя с таким id нет в базе")

		user_dict = user_list[0]
		user_info = User(self._user_id, user_dict["username"],
						user_dict["hashed_password"], user_dict["salt"],
						user_dict["registration_date"])
		return user_info

	@property
	def wallets(self):
		try:
			with open(PORTFOLIOS_DIR, "r") as f:
				portfolios_dict = json.load(f)
			user_portfolio = [user for user in portfolios_dict
			                  if user["user_id"] == self._user_id]
		except FileNotFoundError:
			print("Файл с данными на пользователя с таким id не найден")

		return self._wallets.copy()




