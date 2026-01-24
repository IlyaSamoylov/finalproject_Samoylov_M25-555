import datetime

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.models import User, Portfolio
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.core.exceptions import ApiRequestError, WalletNotFoundError
from valutatrade_hub.infra.database import DBManager
from valutatrade_hub.decorators import log_action

# TODO: здесь, пока не напишем доступ к курсам через API или что там
class RatesService:

	def __init__(self):
		self._settings = SettingsLoader()
		# TODO: не забудь вернуть правильный TTl в pyproject
		self.cache_ttl = datetime.timedelta(seconds=self._settings.get("rates_ttl_seconds"))
		self._db = DBManager()

	def get_rate(self, from_: str, to: str) -> float:

		if not isinstance(from_, str) or not isinstance(to, str):
			raise TypeError("Коды валют должны быть строками")

		if from_ == to:
			return 1.0

		rates = self._load_rates()

		key = f"{from_}_{to}"
		reverse_key = f"{to}_{from_}"

		# если валюта есть, но курс недоступен
		if key not in rates and reverse_key not in rates:
			raise ApiRequestError(f"Курс {from_}->{to} недоступен")

		rate_entry = rates.get(key) or rates.get(reverse_key)

		if not self.is_cache_fresh(rate_entry):
			raise ApiRequestError("Курс недоступен: кеш устарел")

		if key in rates:
			return rates[key]["rate"]

		return 1 / rates[reverse_key]["rate"]

	def _load_rates(self) -> dict:
		try:
			return self._db.load_rates()
		except FileNotFoundError:
			raise ApiRequestError("Курсы недоступны")

	def is_cache_fresh(self, rate: dict) -> bool:

		last_refresh_str = rate.get("updated_at")

		if not last_refresh_str:
			return False

		last_refresh = datetime.datetime.fromisoformat(last_refresh_str)
		if last_refresh.tzinfo is None:
			last_refresh = last_refresh.replace(tzinfo=datetime.UTC)

		return datetime.datetime.now(datetime.UTC) - last_refresh < self.cache_ttl

	def get_rate_pair(self, from_: str, to: str) -> dict:
		"""
		Возвращает:
		{
			"rate": float,
			"reverse_rate": float,
			"updated_at": datetime
		}
		"""
		key = f"{from_}_{to}"
		reverse_key = f"{to}_{from_}"

		rates = self._load_rates()

		# хотя бы один - прямой/обратный курс в rates есть
		if key not in rates and reverse_key not in rates:
			raise ApiRequestError(f"Курс {from_}->{to} недоступен")

		# rate из двух, который есть в rates:
		ex_rate = rates.get(key) or rates.get(reverse_key)

		if not self.is_cache_fresh(ex_rate):
			raise ApiRequestError("Курс недоступен: кеш устарел и Parser недоступен")

		# либо курс есть в rate и его берем, либо нет, тогда считаем по второму
		req_rate = rates.get(key).get("rate") if rates.get(key) else 1 / rates[reverse_key]["rate"]
		reverse_rate = rates.get(reverse_key).get("rate") if rates.get(reverse_key) else 1 / rates[key]["rate"]
		updated_at = datetime.datetime.fromisoformat(ex_rate["updated_at"])

		return {
			"rate": req_rate,
			"reverse_rate": reverse_rate,
			"updated_at": updated_at,
		}

# TODO: Как-то бы где-то отображать что ли, кто за рулем, раз теперь можно менять пользователей как перчатки
class UseCases:
	def __init__(self, rates_service: RatesService, current_user: User | None = None,
	             current_portfolio: Portfolio | None = None):
		self._rates_service = rates_service
		self._settings = SettingsLoader()
		self._base_currency = self._settings.get("default_base_currency")
		self._db = DBManager()

		user_id = self._db.load_session()
		if user_id:
			user_dict = self._db.get_user_by_id(user_id)
			if user_dict:
				self._current_user = User.from_dict(user_dict)
				portfolio_dict = self._db.load_portfolio(self._current_user)
				self._current_portfolio = Portfolio.from_dict(self._current_user, portfolio_dict)
			else:
				self._db.clear_session()
				self._current_user = None
				self._current_portfolio = None
		else:
			self._current_user = None
			self._current_portfolio = None
	@log_action("REGISTER")
	def register(self, username:  str, password: str):
		# password и username валидируются при инициализации экземпляра класса User ниже

		new_user = self._db.create_user(username, password)

		new_portfolio = Portfolio(new_user)
		new_portfolio.add_currency(self._base_currency, init_balance=100.00)

		self._db.create_portfolio(new_portfolio)

		# TODO: наверное лучше будет вернуть консоли сообщение для вывода на экран
		print(f"Пользователь '{username}' зарегистрирован (id={new_user.user_id}). "
				f"Войдите: login --username {username} --password", len(password)*"*")

	@log_action("LOGIN")
	def login(self, username: str, password: str):

		user_dict = self._db.get_user_by_username(username)
		if user_dict is None:
			raise ValueError(f"Пользователь '{username}' не найден")

		user = User.from_dict(user_dict)

		if not user.verify_password(password):
			raise ValueError("Неверный пароль")

		self._current_user = user

		portfolio = self._db.load_portfolio(user)
		if portfolio is None:
			raise RuntimeError("Портфель пользователя отсутствует")

		portfolio = Portfolio.from_dict(self._current_user, portfolio)

		self._current_portfolio = portfolio
		self._db.save_session(user.user_id)

		print(f"Вы вошли как '{username}'")

	@log_action("LOGOUT")
	def logout(self):
		if self._db.load_session():
			print(f"Вы вышли из аккаунта {self._current_user.username}")
			self._current_user = None
			self._current_portfolio = None
			self._db.clear_session()
		else:
			print("Вы еще не входили в аккаунт")

	def show_portfolio(self, base: str | None  = None):
		if base is None:
			base = self._base_currency

		if not self._current_user:
			raise ValueError("Сначала выполните login")

		if not self._current_portfolio.wallets:
			raise ValueError(f"Портфель пуст")

		currency = get_currency(base)

		return self._current_portfolio.view(currency.code, self._rates_service)

	@log_action("BUY", verbose=True)
	def buy(self, currency: str, amount: float):

		if not self._current_user:
			raise ValueError("Сначала нужно зарегистрироваться")

		if currency == self._base_currency:
			raise ValueError(f"{currency} - базовая валюта, ее нельзя купить, только пополнить")

		# amount уже валидируется в CLI
		if amount <= 0:
			raise ValueError("'amount' должен быть положительным числом")

		# валидация валюты сейчас - ответственность валюты
		currency = get_currency(currency)
		currency_code = currency.code

		portfolio = self._current_portfolio
		if not portfolio:
			raise RuntimeError("Портфель пользователя не загружен")

		# курс currency → USD
		rate = self._rates_service.get_rate(currency_code, self._base_currency)
		cost_usd = amount * rate

		usd_wallet = portfolio.get_or_create_wallet(self._base_currency)

		# если кошелька для этой валюты нет - создадим
		wallet = portfolio.get_or_create_wallet(currency_code)

		before = wallet.balance

		usd_wallet.withdraw(cost_usd)
		wallet.deposit(amount)
		after = wallet.balance

		self._db.save_portfolio(portfolio)

		return {
			"currency": currency_code,
			"before": before,
			"after": after,
			"rate": rate,
			"cost": cost_usd,
		}

	@log_action("SELL", verbose=True)
	def sell(self, currency:str, amount:float):
		if not self._current_user:
			raise ValueError("Сначала нужно зарегистрироваться")

		if currency == self._base_currency:
			raise ValueError(f"{currency} - базовая валюта, ее нельзя продать, только пополнить")
		if amount <= 0:
			raise ValueError("'amount' должен быть положительным числом")

		# валидация валюты
		currency = get_currency(currency)
		currency_code = currency.code

		portfolio = self._current_portfolio
		if not portfolio:
			raise RuntimeError("Портфель пользователя не загружен")

		if not portfolio.has_wallet(currency_code):
			raise WalletNotFoundError(currency_code)

		wallet = portfolio.get_wallet(currency_code)

		usd_wallet = portfolio.get_wallet(self._base_currency)

		before = wallet.balance
		wallet.withdraw(amount)
		after = wallet.balance

		# расчетная стоимость

		rate = self._rates_service.get_rate(currency_code, self._base_currency)
		cost = amount * rate
		usd_wallet.deposit(cost)

		self._db.save_portfolio(portfolio)

		return {
			"currency": currency_code,
			"before": before,
			"after": after,
			"rate": rate,
			"cost": cost,
		}

	def get_rate(self, from_v:str, to:str):
		from_currency = get_currency(from_v)
		to_currency = get_currency(to)

		return self._rates_service.get_rate_pair(from_currency.code, to_currency.code)

	@log_action("DEPOSIT", verbose=True)
	def deposit(self, amount):
		if not self._current_user:
			raise ValueError("Сначала нужно зарегистрироваться")

		portfolio = self._current_portfolio
		if not portfolio:
			raise RuntimeError("Портфель пользователя не загружен")

		usd_wallet = portfolio.get_or_create_wallet(self._base_currency)

		before = usd_wallet.balance
		usd_wallet.deposit(amount)
		after = usd_wallet.balance

		self._db.save_portfolio(portfolio)

		return {
			"currency": self._base_currency,
			"before": before,
			"after": after,
			"amount": amount,
		}
# TODO: все таки в buy/sell/deposit использовать "USD", base_currency из settings или