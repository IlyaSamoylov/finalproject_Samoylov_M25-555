from __future__ import annotations

import hashlib
import secrets
from datetime import datetime

from valutatrade_hub.core.exceptions import InsufficientFundsError


class User:
	"""
		Модель пользователя
    """
	def __init__(self, user_id: int, username: str, password: str,
					registration_date: datetime | None = None):
		"""
		Инициализация пользователя, назначение атрибутов
		Args:
			user_id: уникальный идентификатор пользователя
			username: имя пользователя
			password: пароль
			registration_date: дата регистрации, если известна, иначе - ставится now
		"""
		self._user_id = user_id
		# _username устанавливается через setter - внутри валидируется:
		self.username = username
		self._salt = self._generate_salt()
		# пароль валидируется в приватном методе, а затем в другом из него делается хэш
		self._hashed_password = self._hash(self._validate_pword(password))
		self._registration_date = registration_date if registration_date is not None \
			else datetime.now()

	@property
	def user_id(self):
		"""
		Возвращает идентификатор пользователя

		Returns:
			int: ID пользователя
		"""
		return self._user_id

	@property
	def username(self):
		"""
		Возвращает имя пользователя

		Returns:
			str: имя пользователя
		"""
		return self._username

	@username.setter
	def username(self, uname: str):
		"""
		Валидирует и устанавливает имя пользователя

		Args:
			uname: новое имя пользователя
		"""
		# валидация username
		if not isinstance(uname, str) or not uname.strip():
			raise ValueError("Имя не может быть пустым")

		self._username = uname

	@property
	def hashed_password(self):
		"""
		Возвращает хэш пароля

		Returns:
			str: хэш пароля
		"""
		return self._hashed_password

	@property
	def salt(self):
		"""
		Возвращает соль, которая использовалась для хэширования пароля

		Returns:
			str: соль
		"""
		return self._salt

	@property
	def registration_date(self):
		"""
		Возвращает дату регистрации пользователя

		Returns:
            datetime: дата регистрации
		"""
		return self._registration_date

	def get_user_info(self):
		"""
		Возвращает публичную информацию о пользователе без пароля

		Returns:
			dict: информация о пользователе
		"""
		return {
			"User ID": self.user_id,
			"Username": self.username,
			"Registration Date": self.registration_date
		}

	def _validate_pword(self, pword: str):
		"""
		Валидирует пароль

		Args:
			pword: пароль на проверку

		Returns:
			str: валидный пароль
		"""
		if not isinstance(pword, str) or len(pword.strip()) < 4:
			raise ValueError("Неверный формат password")
		return pword

	@staticmethod
	def _generate_salt():
		"""
		Генерация соли для хэширования паролей

		Returns:
			str: Случайная соль
		"""
		return secrets.token_hex(8)

	def change_password(self, new_password: str):
		"""
		Изменяет пароль пользователя с обновлением соли

		Args:
			new_password: новый пароль
		"""
		self._salt = self._generate_salt()
		self._hashed_password = self._hash(self._validate_pword(new_password))

	def verify_password(self, password: str):
		"""
		Проверяет пароль

		Args:
			password: введенный парль
		Returns:
			bool: True, если пароль верный
		"""
		return self._hash(password) == self._hashed_password

	def _hash(self, password: str) -> str:
		"""
		Хэширует пароль с использованием соли

		Args:
			password: пароль
		Returns:
			str: SHA-256 хэш.
		"""
		return hashlib.sha256(password.encode() + self._salt.encode()).hexdigest()

	@classmethod
	def from_dict(cls, u_dict) -> User:
		"""
		Создает пользователя из словаря

		Args:
			u_dict:
		Returns:
			User: экземпляр пользователя
		"""
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
		"""
		Преобразует пользователя в формат словаря

		Returns:
			dict: словарь с данными пользователя
		"""
		u_dict = {
			"user_id": self.user_id,
			"username": self.username,
			"hashed_password": self.hashed_password,
			"salt": self.salt,
			"registration_date": self.registration_date.isoformat()
		}
		return u_dict

class Wallet:
	"""
	Модель кошелька пользователя для конкретной валюты.
	"""
	def __init__(self, currency_code: str, balance: float = 0.0):
		"""
		Создает кошелек с начальным балансом balance

		Args:
			currency_code (str): валюта
			balance (float): начальный баланс
		"""

		if not isinstance(currency_code, str) or not currency_code.strip():
			raise ValueError("Некорректный код валюты")

		self.currency_code = currency_code
		self.balance = balance # инициируется через сеттер с валидацией

	@property
	def balance(self):
		"""
		Возвращает баланс на кошельке

		Returns:
			float: баланс на кошельке
		"""
		return self._balance

	@balance.setter
	def balance(self, value: float):
		"""
		Валидирует и устанавливает баланс

		Args:
			value (float): новое значение баланса
		"""
		if not isinstance(value, (int, float)):
			raise ValueError("Некорректный тип данных")
		if value < 0:
			raise ValueError("Баланс не может быть меньше 0")
		self._balance = value

	def deposit(self, amount: float):
		"""
		Пополнить баланс кошелька

		Args:
			amount (float): сумма пополнения
		"""
		if not isinstance(amount, (int, float)):
			raise ValueError("'Количество' денег должно быть числом")
		if amount <= 0:
			raise ValueError("Нельзя положить отрицательное количество денег")

		self._balance += amount

	def withdraw(self, amount: float):
		"""
		Списать средства с кошелька

		Args:
			amount (float): сумма списания
		"""
		if not isinstance(amount, (int, float)):
			raise TypeError("Сумма должна быть числом")
		if amount <= 0:
			raise ValueError("Сумма снятие не может быть меньше или равна 0")
		if amount > self.balance:
			raise InsufficientFundsError(self.balance, self.currency_code ,amount)
		self._balance -= amount

	def get_balance_info(self):
		"""
		Вывод баланса кошелька
		Returns dict: {
			"currency code":
			"balance":
		} : валюта кошелька и баланс
		"""
		return {
			"currency code": self.currency_code,
			"balance": self._balance
		}

	@classmethod
	def from_dict(cls, w_dict: dict, cur_code: str = 'USD') -> Wallet:
		"""
		Создает кошелек из словаря

		Args:
			w_dict (dict): данные кошелька
			cur_code (str): код валюты
		Returns:
			Wallet: кошелек из словаря
		"""
		return cls(currency_code=cur_code, balance=w_dict.get("balance", 0.0))

	def to_dict(self):
		"""
		Сериализация кошелька в словарь

		Returns:
			dict: данные кошелька
		"""
		return {"balance": self._balance}


class Portfolio:
	"""
	Класс портфеля пользователя. Содержит набор кошельков, связанных с пользователем
	"""
	def __init__(self, user: User, wallets: dict[str, Wallet] | None = None):
		"""
		Создает портфель пользователя

		Args:
			user (User): владелец портфеля
			wallets (dict[str, Wallet] | None): словарь кошельков пользователя
		"""
		self._user = user
		self._wallets = wallets if wallets is not None else {}

	def add_wallet(self, currency_code: str, init_balance: float = 0.0):
		"""
		Добавляет новый валютный кошелек

		Args:
			currency_code (str): код валюты
			init_balance (float): изначальный баланс на кошельке
		Returns:
			Wallet: созданный кошелек
		"""
		if self.has_wallet(currency_code):
			raise ValueError(f"Кошелёк {currency_code} уже существует")
		wallet = Wallet(currency_code, init_balance)
		self._wallets[currency_code] = wallet
		return wallet

	def get_total_value(self, exchange_rates: dict, base_currency="USD"):
		"""
		Вычисляет общую стоимость портфеля в базовой валюте

		Args:
			exchange_rates (dict): курсы валют
			base_currency (str): базовая валюта
		Returns:
			float: общая стоимость портфеля в базовой валюте
		"""
		total = 0.0
		for wallet in self._wallets.values():
			rate = exchange_rates[wallet.currency_code][base_currency]
			total += wallet.balance * rate
		return total

	def has_wallet(self, currency_code: str) -> bool:
		"""
		Проверка наличия валютного кошелька

		Args:
			currency_code (str): код валюты для проверки
		Returns:
			bool: true, если кошелек существует
		"""
		return currency_code in self._wallets

	def get_wallet(self, currency_code: str) -> Wallet:
		"""
		Получить кошелек по коду валюты

		Args:
			currency_code (str): код валюты
		Returns:
			Wallet: валютный кошелек
		"""
		if not self.has_wallet(currency_code):
			raise ValueError(f"Кошелёк {currency_code} не найден")
		return self._wallets[currency_code]

	@property
	def user(self) -> User:
		"""
		Вернуть пользователя портфеля

		Returns:
			User: пользователь портфеля
		"""
		return self._user

	@property
	def wallets(self) -> dict[str, Wallet]:
		"""
		Возвращает копию словаря кошельков

		Returns:
			dict[str, Wallet]: словарь кошельков пользователя
		"""
		return self._wallets.copy()

	@classmethod
	def from_dict(cls, user: User, data: dict) -> Portfolio:
		"""
		Возвращает портфель из словаря

		Returns:
			Portfolio: портфель из словаря
		"""
		wallets = {
			code: Wallet.from_dict(w_data, code)
			for code, w_data in data.get("wallets", {}).items()
		}
		return cls(user, wallets)

	def to_dict(self) -> dict:
		"""
		Сериализация портфеля в словарь

		Returns:
			dict: данные портфеля
		"""
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
		Формирует представление портфеля в базовой валюте.

		Args:
			base (str): Базовая валюта.
			rates_service (RatesService): Сервис курсов.

		Returns:
			tuple: (список валют, общая сумма).
		"""
		items = []
		total = 0.0
		for wallet in self.wallets.values():
			rate = rates_service.get_rate(wallet.currency_code, base).get("rate")
			converted = wallet.balance * rate
			items.append((wallet.currency_code, wallet.balance, converted))
			total += converted

		return items, total

	def get_or_create_wallet(self, currency: str) -> Wallet:
		"""
		Возвращает существующий кошелк или создает новый

		Args:
			currency (str): код валюты
		Returns:
			Wallet: кошелек пользователя
		"""
		if not self.has_wallet(currency):
			return self.add_wallet(currency)
		return self.get_wallet(currency)

