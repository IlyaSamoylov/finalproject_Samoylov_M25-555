from __future__ import annotations

from datetime import datetime
import hashlib
import secrets

from valutatrade_hub.core.exceptions import InsufficientFundsError

class User:
	# todo: убедиться, что User будут передаваться правильные форматы date/password
	def __init__(self, user_id: int, username: str, password: str,
				registration_date: datetime | None = None):

		# TODO: user_id должен быть уникальным, это будет контролироваться в usecases
		self._user_id = user_id
		# _username устанавливается через setter - внутри валидируется:
		self.username = username
		self._salt = self._generate_salt()
		# пароль валидируется в приватном методе, а затем в другом из него делается хэш
		self._hashed_password = self._hash(self._validate_pword(password))
		# дата регистрации устанаваливается как передана, если не передана, то устанавливается сейчас
		self._registration_date = registration_date if registration_date is not None \
			else datetime.now()

	@property
	def user_id(self):
		return self._user_id

	@property
	def username(self):
		return self._username

	@username.setter
	def username(self, uname: str):
		# валидация username
		if not isinstance(uname, str) or not uname.strip():
			raise ValueError("Имя не может быть пустым")

		self._username = uname

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

	def _validate_pword(self, pword: str):
		# валидация введенного пароля
		if not isinstance(pword, str) or len(pword.strip()) < 4:
			raise ValueError("Неверный формат password")
		return pword

	@staticmethod
	def _generate_salt():
		"""Генерация соли для хэширования паролей"""
		return secrets.token_hex(8)

	def change_password(self, new_password: str):
		self._salt = self._generate_salt()
		self._hashed_password = self._hash(self._validate_pword(new_password))

	def verify_password(self, password: str):
		return self._hash(password) == self._hashed_password

	def _hash(self, password: str) -> str:
		return hashlib.sha256(password.encode() + self._salt.encode()).hexdigest()

	@classmethod
	def from_dict(cls, u_dict) -> User:
		user = cls.__new__(cls)

		user._user_id = u_dict["user_id"]
		user._username = u_dict["username"]
		user._hashed_password = u_dict["hashed_password"]
		user._salt = u_dict["salt"]
		user._registration_date = datetime.fromisoformat(
			u_dict["registration_date"]
		)

		return user

	def to_dict(self):
		u_dict = {
			"user_id": self.user_id,
			"username": self.username,
			"hashed_password": self.hashed_password,
			"salt": self.salt,
			"registration_date": self.registration_date.isoformat()
		}
		return u_dict

	def session_info(self) -> dict:
		"""Метод для передачи краткой публичной информации о пользователе.
		Например, для установки сессии"""
		return {
			"user_id": self._user_id,
			"username": self._username
		}

class Wallet:
	def __init__(self, currency_code: str, balance: float = 0.0):

		if not isinstance(currency_code, str) or not currency_code.strip():
			raise ValueError("Некорректный код валюты")

		self.currency_code = currency_code
		self.balance = balance # инициируется через сеттер с валидацией

	def deposit(self, amount:float):
		if not isinstance(amount, (int, float)):
			raise ValueError("'Количество' денег должно быть числом")
		if amount <= 0:
			raise ValueError("Нельзя положить отрицательное количество денег")

		self._balance += amount

	def withdraw(self, amount: float):
		if not isinstance(amount, (int, float)):
			raise TypeError("Сумма должна быть числом")
		if amount <= 0:
			raise ValueError("Сумма снятие не может быть меньше или равна 0")
		if amount > self.balance:
			# поменял исключение, правильно?
			raise InsufficientFundsError(self.balance, self.currency_code ,amount)
		self._balance -= amount

	def get_balance_info(self):
		return {
			"currency code": self.currency_code,
			"balance": self._balance
		}

	@property
	def balance(self):
		return self._balance

	@balance.setter
	def balance(self, value: float):
		if not isinstance(value, (int, float)):
			raise ValueError("Некорректный тип данных")
		if value < 0:
			raise ValueError("Баланс не может быть меньше 0")
		self._balance = value

	@classmethod
	def from_dict(cls, w_dict: dict, cur_code: str = 'USD') -> Wallet:
		return cls(currency_code=cur_code, balance=w_dict.get("balance", 0.0))

	def to_dict(self):
		return {"balance": self._balance}


class Portfolio:
	# TODO: или вместо user нужен user_id все таки? Дальше глянем
	def __init__(self, user: User, wallets: dict[str, Wallet] | None = None):
		self._user = user
		self._wallets = wallets if wallets is not None else {}

	def add_currency(self, currency_code: str, init_balance: float = 0.0):
		if self.has_wallet(currency_code):
			raise ValueError(f"Кошелёк {currency_code} уже существует")
		wallet = Wallet(currency_code, init_balance)
		self._wallets[currency_code] = wallet
		return wallet

	def get_total_value(self, exchange_rates: dict, base_currency="USD"):
		total = 0.0
		for wallet in self._wallets.values():
			rate = exchange_rates[wallet.currency_code][base_currency]
			total += wallet.balance * rate
		return total

	def has_wallet(self, currency_code: str) -> bool:
		return currency_code in self._wallets

	def get_wallet(self, currency_code: str) -> Wallet:
		if not self.has_wallet(currency_code):
			raise ValueError(f"Кошелёк {currency_code} не найден")
		return self._wallets[currency_code]

	@property
	def user(self) -> User:
		return self._user

	@property
	def wallets(self) -> dict[str, Wallet]:
		return self._wallets.copy()

	@classmethod
	def from_dict(cls, user: User, data: dict) -> Portfolio:
		wallets = {
			code: Wallet.from_dict(code, w_data)
			for code, w_data in data.get("wallets", {}).items()
		}
		return cls(user, wallets)

	def to_dict(self) -> dict:
		return {
			"user_id": self.user.user_id,
			"wallets": {
				code: wallet.to_dict()
				for code, wallet in self._wallets.items()
			}
		}

	def view(self, base: str, rates_service) -> tuple[
		list[tuple[str, float, float]], float]:
		"""
		Возвращает:
		- список (currency, balance, converted_to_base)
		- total в base
		"""
		items = []
		total = 0.0
		for wallet in self.wallets.values():
			rate = rates_service.get_rate(wallet.currency_code, base)
			converted = wallet.balance * rate
			items.append((wallet.currency_code, wallet.balance, converted))
			total += converted

		return items, total

	def get_or_create_wallet(self, currency: str) -> Wallet:
		if not self.has_wallet(currency):
			return self.add_currency(currency)
		return self.get_wallet(currency)

