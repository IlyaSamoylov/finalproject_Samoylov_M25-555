import datetime

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import ApiRequestError, WalletNotFoundError
from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.database import DBManager
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.parser_service.api_clients import PARSER_CLIENT_REGISTRY
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import RatesStorage
from valutatrade_hub.parser_service.updater import RatesUpdater


class RatesService:
	"""
	Сервис работы с курсами валют.

	Отвечает за:
	- получение курсов из .json
	- проверку актуальности курсов по TTL
	- вычисление прямого и обратного курсов
	"""
	def __init__(self):
		"""
		Инициализация сервиса работы с курсами.
		"""
		self._settings = SettingsLoader()
		self.cache_ttl = datetime.timedelta(
			seconds=self._settings.get("rates_ttl_seconds")
		)
		self._db = DBManager()

	def get_rate(self, from_: str, to: str) -> float:
		"""
		Возвращает курс
		Args:
			from_ (str): код исходной валюты
			to (str): код целевой валюты

		Return:
			float: курс from_ -> to
		"""
		if not isinstance(from_, str) or not isinstance(to, str):
			raise TypeError("Коды валют должны быть строками")

		if from_ == to:
			return 1.0

		rates = self._load_rates().get("pairs")

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
		"""
		Загрузить курсы валют из rates.json
		Returns:
			dict: курсы валют
		"""
		try:
			return self._db.load_rates()
		except FileNotFoundError:
			raise ApiRequestError("Курсы недоступны")

	def is_cache_fresh(self, rate: dict) -> bool:
		"""
		Проверить свежесть курсов. Обновиться курсы должны не раньше, чем TTL
		Args:
			rate (dict): курсы, которые нужно проверить
		Returns:
			bool: свежие курсы или нет
		"""
		last_refresh_str = rate.get("updated_at")

		if not last_refresh_str:
			return False

		last_refresh = datetime.datetime.fromisoformat(last_refresh_str)
		if last_refresh.tzinfo is None:
			last_refresh = last_refresh.replace(tzinfo=datetime.UTC)

		return datetime.datetime.now(datetime.UTC) - last_refresh < self.cache_ttl

	def get_rate_pair(self, from_: str, to: str) -> dict:
		"""
		Возвращает пару курсов - прямой и обратный, между валютами
		Args:
			from_ (str): исходная валюта
			to (str): целевая валюта
		Returns:
			dict: {
					"rate": float,
					"reverse_rate": float,
					"updated_at": datetime
			}
		"""
		key = f"{from_}_{to}"
		reverse_key = f"{to}_{from_}"

		rates = self._load_rates().get("pairs")
		# хотя бы один - прямой/обратный курс в rates есть
		if key not in rates and reverse_key not in rates:
			raise ApiRequestError(f"Курс {from_}->{to} недоступен")

		# rate из двух, который есть в rates:
		ex_rate = rates.get(key) or rates.get(reverse_key)

		if not self.is_cache_fresh(ex_rate):
			raise ApiRequestError("Курс недоступен: кеш устарел и Parser недоступен")

		# либо курс есть в rate и его берем, либо нет, тогда считаем по второму
		req_rate = rates.get(key).get("rate") if rates.get(key) \
			else 1 / rates[reverse_key]["rate"]
		reverse_rate = rates.get(reverse_key).get("rate") if rates.get(reverse_key) \
			else 1 / rates[key]["rate"]
		updated_at = datetime.datetime.fromisoformat(ex_rate["updated_at"])

		return {
			"rate": req_rate,
			"reverse_rate": reverse_rate,
			"updated_at": updated_at,
		}

class UseCases:
	"""
	Слой бизнес-логики приложения
	Описывает сценарии использования системы.
	"""
	def __init__(self, rates_service: RatesService, current_user: User | None = None,
					current_portfolio: Portfolio | None = None):
		"""
		Инициализация
		Args:
			rates_service (RatesService): сервис работы с курсами валют
			currenct_user (User): текущий пользователь, занимающий сессию
			currenct_portfolio (Portfolio): портфель текущенго пользователя
		"""
		self._rates_service = rates_service
		self._settings = SettingsLoader()
		self._base_currency = self._settings.get("default_base_currency")
		self._db = DBManager()
		self._parser_config = ParserConfig()

		user_id = self._db.load_session()
		if user_id:
			user_dict = self._db.get_user_by_id(user_id)
			if user_dict:
				self._current_user = User.from_dict(user_dict)
				portfolio_dict = self._db.load_portfolio(self._current_user)
				self._current_portfolio = Portfolio.from_dict(self._current_user,
                  portfolio_dict) if portfolio_dict else Portfolio(self._current_user)
			else:
				self._db.clear_session()
				self._current_user = None
				self._current_portfolio = None
		else:
			self._current_user = None
			self._current_portfolio = None

	@log_action("REGISTER")
	def register(self, username:  str, password: str):
		"""
		Регистрация нового пользователя и создание для него стартового портфеля.
		Для решения проблемы невозможности купить/продать что-то с пустым портфелем,
		в качестве подарка за регистрацию выдается 100 базовой валюты
		Args:
			username (str): имя пользователя
			password (str): пароль
		"""
		# password и username валидируются при инициализации экземпляра класса User ниже

		new_user = self._db.create_user(username, password)

		new_portfolio = Portfolio(new_user)
		new_portfolio.add_currency(self._base_currency, init_balance=100.00)

		self._db.create_portfolio(new_portfolio)

		print(f"Пользователь '{username}' зарегистрирован (id={new_user.user_id}). "
				f"Войдите: login --username {username} --password", len(password)*"*")

	@log_action("LOGIN")
	def login(self, username: str, password: str):
		"""
		Выполняет вход существующего пользователя и загружает его портфель

		Args:
			username (str): имя пользователя
			password (str): пароль
		"""
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
		"""
		Выполняет выход пользователя из аккаунта и обнуление сессии
		"""
		if self._current_user:
			print(f"Вы вышли из аккаунта {self._current_user.username}")
			self._current_user = None
			self._current_portfolio = None
			self._db.clear_session()
		else:
			print("Вы еще не входили в аккаунт")

	def show_portfolio(self, base: str | None  = None):
		"""
		Возвращает содержимое портфеля пользователя.

		Args:
			base (str | None): базовая валюта для перерасчета
		Returns:
			tuple: представление портфеля и итоговую цену
		"""
		if base is None:
			base = self._base_currency

		if not self._current_user:
			raise ValueError("Сначала выполните login")

		if not self._current_portfolio.wallets:
			raise ValueError("Портфель пуст")

		currency = get_currency(base)

		return self._current_portfolio.view(currency.code, self._rates_service)

	@log_action("BUY", verbose=True)
	def buy(self, currency: str, amount: float) -> dict:
		"""
		Покупка валюты за базовую валюту.Покупка незалогиненному пользователю запрещена.
		Купить базовую валюту нельзя.
		Автоматически создает соответствующий кошелек при первой покупке валюты.
		Args:
			currency (str):  базовая валюта перерасчета
			amount (float): количество покупаемой валюты

		Returns:
			dict: {
			"currency": currency_code,
			"before": before,
			"after": after,
			"rate": rate,
			"cost": cost_usd,
		} : информация об операции: валюта, до/после покупки, курс покупки, выручка
		"""
		if not self._current_user:
			raise ValueError("Сначала нужно зарегистрироваться")

		if currency == self._base_currency:
			raise ValueError(f"{currency} - базовая валюта, ее нельзя купить, только "
								f"пополнить")

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
			"cost": cost_usd
		}

	@log_action("SELL", verbose=True)
	def sell(self, currency:str, amount:float) -> dict:
		"""
		Продать валюту и зачислить средства в базовую валюту.

		Args:
			currency (str): валюта
			amount (float): количество валюты
		Returns:
			dict: return {
			"currency": currency_code,
			"before": before,
			"after": after,
			"rate": rate,
			"cost": cost,
		} : валюта, до/после продажи, курс продажи, выручка
		"""
		if not self._current_user:
			raise ValueError("Сначала нужно зарегистрироваться")

		if currency == self._base_currency:
			raise ValueError(f"{currency} - базовая валюта, ее нельзя продать, только "
								f"пополнить")
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
			"cost": cost
		}

	def get_rate(self, from_v:str, to:str):
		"""
		Возвращает курс между двумя валютами с помощью RatesService.
		Args:
			from_v: код исходной валюты
			to: код целевой валюты
		Returns:
			dict: {
					"rate": float,
					"reverse_rate": float,
					"updated_at": datetime
			}
		"""
		from_currency = get_currency(from_v)
		to_currency = get_currency(to)

		return self._rates_service.get_rate_pair(from_currency.code, to_currency.code)

	def update_rates(self, source: str | None = None) -> None:
		"""
		Обновить курсы валют через ParserService

		Args:
			source (str): источник обновления курсов. Если None - обновить по всем
		"""
		config = ParserConfig()
		clients = []

		if source is None:
			for client_cls in PARSER_CLIENT_REGISTRY.values():
				clients.append(client_cls(config))
		else:
			key = source.lower()
			client_cls = PARSER_CLIENT_REGISTRY.get(key)

			if not client_cls:
				raise ValueError(
					f"Неизвестный источник обновления: {source}. "
					f"Доступные источники: {', '.join(PARSER_CLIENT_REGISTRY)}"
				)

			clients.append(client_cls(config))

		storage = RatesStorage(self._parser_config)
		updater = RatesUpdater(clients, storage)
		updater.run_update(trigger='CLI')

	def show_rates(self, currency: str | None = None, top: int | None = None,
			base: str | None = None) -> list[str]:
		"""
		Возвращает список курсов из хранилища.
		Args:
			currency (str): код валюты, None - все
			top (int): топ самых высоких курсов валют
			base (str): базовая валюта
		Returns:
			list[str]: список курсов валют
		"""

		storage = RatesStorage(self._parser_config)
		data = storage.load_rates()

		pairs = data.get("pairs", {})
		last_refresh = data.get("last_refresh")

		if not pairs:
			raise ValueError(
				"Локальный кеш курсов пуст. Выполните 'update-rates'."
			)

		items = list(pairs.items())

		if currency:
			currency = currency.upper()
			items = [
				(pair, meta)
				for pair, meta in items
				if currency in pair
			]

		if base:
			base = base.upper()
			items = [
				(pair, meta)
				for pair, meta in items
				if pair.endswith(f"_{base}")
			]

		if top:
			items.sort(key=lambda x: x[1]["rate"], reverse=True)
			items = items[:top]
		else:
			items.sort(key=lambda x: x[0])

		if not items:
			raise ValueError("Запрошенные курсы не найдены")

		result = [f"Курсы из кеша (обновлено {last_refresh}):"]

		for pair, meta in items:
			result.append(
				f"- {pair}: {meta['rate']} (источник: {meta['source']})"
			)

		return result

	@log_action("DEPOSIT", verbose=True)
	def deposit(self, amount: float) -> dict:
		"""
		Пополнение счета базовой валютой. Для решения проблем с недостаточным числом
		средств для купли-продажи, если 100 USD не хватает, например для покупки крипты

		Args:
			amount (float): число базовой валюты для пополнения счета
		Returns:
			dict: {
			"currency": self._base_currency,
			"before": before,
			"after": after,
			"amount": amount,
		} : код валюты, до/после пополнения, число положенных денег
		"""
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

	def whoami(self) -> str:
		"""
		Узнать, какой пользователь сейчас занимает сессию
		Returns:
			str: имя текущего пользователя
		"""
		if not self._current_user:
			return "Вы не авторизованы"
		return f"Текущий пользователь: {self._current_user.username}"