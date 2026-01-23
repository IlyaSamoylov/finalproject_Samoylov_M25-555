import datetime
from pathlib import Path

from valutatrade_hub.core.utils import load, save, set_session
from valutatrade_hub.core.models import User, Wallet, Portfolio
from valutatrade_hub.infra.settings import SettingsLoader
from valutatrade_hub.core.exceptions import CurrencyNotFoundError, InsufficientFundsError, ApiRequestError, WalletNotFoundError
# че, все методы RatesService в try..except c ApiRequestError оборачивать? Или заменить все локальные
# load(RATES_DIR) на метод _load_rates и засунуть в него ApiRequestError? Если решим определить rates_dict
# как атрибут класса RatesService, то даже не знаю, куда девать ApiRequestError
from valutatrade_hub.decorators import log_action

# TODO: здесь, пока не напишем доступ к курсам через API или что там
class RatesService:

	def __init__(self):
		self._settings = SettingsLoader()
		self._rate_dir = Path(self._settings.get("data_dir")) / "rates.json"
		self.cache_ttl = datetime.timedelta(seconds=self._settings.get("rates_ttl_seconds"))

	def get_rate(self, from_: str, to: str) -> float:

		if not isinstance(from_, str) or not isinstance(to, str):
			raise TypeError("Коды валют должны быть строками")

		if from_ == to:
			return 1.0

		self.validate_currency(code=from_)
		self.validate_currency(code=to)

		rates = self._load_rates()

		key = f"{from_}_{to}"
		reverse_key = f"{to}_{from_}"

		# если валюта есть, но курс недоступен
		if key not in rates and reverse_key not in rates:
			raise RuntimeError(f"Курс {from_}->{to} недоступен")

		rate_entry = rates.get(key) or rates.get(reverse_key)

		if not self.is_cache_fresh(rate_entry):
			raise RuntimeError("Курс недоступен: кеш устарел")

		if key in rates:
			return rates[key]["rate"]

		return 1 / rates[reverse_key]["rate"]

	def validate_currency(self, code: str):
		rates = self._load_rates()
		known = set()

		for pair in rates:
			if "_" in pair:
				a, b = pair.split("_")
				known.update([a, b])

		if code not in known:
			raise CurrencyNotFoundError(code)

	def _load_rates(self) -> dict:
		try:
			return load(self._rate_dir)
		except Exception as e:
			raise ApiRequestError(str(e))

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
		self.validate_currency(code=from_)
		self.validate_currency(code=to)

		key = f"{from_}_{to}"
		reverse_key = f"{to}_{from_}"

		rates = self._load_rates()

		# хотя бы один - прямой/обратный курс в rates есть
		if key not in rates and reverse_key not in rates:
			raise RuntimeError(f"Курс {from_}->{to} недоступен")

		# rate из двух, который есть в rates:
		ex_rate = rates.get(key) or rates.get(reverse_key)

		if not self.is_cache_fresh(ex_rate):
			raise RuntimeError("Курс недоступен: кеш устарел и Parser недоступен")

		# либо курс есть в rate и его берем, либо нет, тогда считаем по второму
		req_rate = rates.get(key).get("rate") if rates.get(key) else 1 / rates[reverse_key]["rate"]
		reverse_rate = rates.get(reverse_key).get("rate") if rates.get(reverse_key) else 1 / rates[key]["rate"]
		updated_at = datetime.datetime.fromisoformat(ex_rate["updated_at"])

		return {
			"rate": req_rate,
			"reverse_rate": reverse_rate,
			"updated_at": updated_at,
		}



class UseCases:
	def __init__(self, rates_service: RatesService, current_user: User | None = None,
	             current_portfolio: Portfolio | None = None):
		self._rates_service = rates_service
		self._current_user = current_user
		self._current_portfolio = current_portfolio

		self._settings = SettingsLoader()
		self._base_currency = self._settings.get("default_base_currency")
		self._portfolio_dir = Path(self._settings.get("data_dir")) / "portfolios.json"
		self._users_dir = Path(self._settings.get("data_dir")) / "users.json"

	@staticmethod
	def _load(path: Path):
		return load(path)

	@staticmethod
	def _save(path: Path, data):
		return save(path, data)

	@log_action("REGISTER")
	def register(self, username:  str, password: str):
		# password и username валидируются при инициализации экземпляра класса User ниже

		# загрузка пользователей
		users_lst = self._load(self._users_dir)
		# если вернет None, то есть неизвестный путь
		if users_lst is None:
			# TODO: как развести, когда еще не было добавлено ни одного юзера и когда с
			#  путем к файлу что-то не так?
			#  вернусь к проблемам, когда буду делать загрузчик сессии
			raise ValueError("Проверь путь до user.json либо пока нет ни одного юзера")

		# проверка уникальности username
		if any(u["username"] == username for u in users_lst):
			raise ValueError(f"Имя пользователя '{username}' уже занято")

		# генерация данных пользователя

		user_id = max((u["user_id"] for u in users_lst), default=0) + 1
		new_user = User(user_id, username, password)

		users_lst.append(new_user.to_dict())
		self._save(self._users_dir, users_lst)

		new_portfolio = Portfolio(new_user)
		new_portfolio.add_currency(self._base_currency, init_balance=100.00)
		portfolios_lst = self._load(self._portfolio_dir)
		if portfolios_lst is None:
			portfolios_lst = []

		portfolios_lst.append(new_portfolio.to_dict())
		self._save(self._portfolio_dir, portfolios_lst)

		# TODO: наверное лучше будет вернуть консоли сообщение для вывода на экран
		print(f"Пользователь '{username}' зарегистрирован (id={user_id}). "
				f"Войдите: login --username {username} --password", len(password)*"*")

	@log_action("LOGIN")
	def login(self, username: str, password: str):

		users_lst = self._load(self._users_dir)
		if users_lst is None:
			raise ValueError(f"Сначала необходимо зарегистрироваться")

		# TODO: в будущем напишу dbmanager, который возьмет на себя ответственность
		#  за поиск в базе нужных юзеров и их портфелей, а пока ручками
		user_dict = next((u for u in users_lst if u["username"] == username), None)
		if user_dict is None:
			raise ValueError(f"Пользователь '{username}' не найден")

		user = User.from_dict(user_dict)

		if not user.verify_password(password):
			raise ValueError("Неверный пароль")

		self._current_user = user
		self._current_portfolio = self._load_portfolio(user)
		set_session(user)

		print(f"Вы вошли как '{username}'")

	# TODO: уберем, когда придем к абстракции над БД
	def _load_portfolio(self, user: User) -> Portfolio:
		raw_portfolios = self._load(self._portfolio_dir)

		for item in raw_portfolios:
			if item["user_id"] == user.user_id:
				wallets = {
					code: Wallet(currency_code=code,
								 balance=data["balance"])
					for code, data in item["wallets"].items()
				}
				return Portfolio(user=user, wallets=wallets)

		# если портфель не найден — возвращаем пустой
		return Portfolio(user=user, wallets={})

	def show_portfolio(self, base: str | None  = None):
		if base is None:
			base = self._base_currency
		# TODO: где будет проверяться base? - наверное, где-то в Currency
		if not self._current_user:
			raise ValueError("Сначала выполните login")

		if not self._current_portfolio.wallets:
			raise ValueError(f"Портфель пуст")

		self._rates_service.validate_currency(base)

		return self._current_portfolio.view(base, self._rates_service)

	@log_action("BUY", verbose=True)
	def buy(self, currency: str, amount: float):

		if not self._current_user:
			raise ValueError("Сначала нужно зарегистрироваться")

		if currency == self._base_currency:
			raise ValueError(f"{currency} - базовая валюта, ее нельзя купить, только пополнить")

		# amount уже валидируется в CLI
		if amount <= 0:
			raise ValueError("'amount' должен быть положительным числом")

		# валидация валюты сейчас - ответственность курсов
		self._rates_service.validate_currency(code=currency)

		portfolio = self._current_portfolio
		if not portfolio:
			raise RuntimeError("Портфель пользователя не загружен")

		# курс currency → USD
		rate = self._rates_service.get_rate(currency, self._base_currency)
		cost_usd = amount * rate

		# TODO: не уверен, стоит ли тут менять на self._base_currency, потому что..
		usd_wallet = portfolio.get_or_create_wallet(self._base_currency)

		wallet = portfolio.get_or_create_wallet(currency)

		before = wallet.balance

		usd_wallet.withdraw(cost_usd)
		wallet.deposit(amount)
		after = wallet.balance

		self._save_portfolio(portfolio)

		return {
			"currency": currency,
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

		# валидация валюты сейчас - ответственность курсов
		self._rates_service.validate_currency(code=currency)

		portfolio = self._current_portfolio
		if not portfolio:
			raise RuntimeError("Портфель пользователя не загружен")

		if not portfolio.has_wallet(currency):
			raise WalletNotFoundError(currency)

		wallet = portfolio.get_wallet(currency)
		# TODO: точно стоит менять на self._base_currency?
		usd_wallet = portfolio.get_wallet(self._base_currency)

		before = wallet.balance
		wallet.withdraw(amount)
		after = wallet.balance

		# расчетная стоимость
		# TODO: точно стоит менять на self._base_currency?
		rate = self._rates_service.get_rate(currency, self._base_currency)
		cost = amount * rate
		usd_wallet.deposit(cost)

		self._save_portfolio(portfolio)

		return {
			"currency": currency,
			"before": before,
			"after": after,
			"rate": rate,
			"cost": cost,
		}

	def get_rate(self, from_v:str, to:str):

		# if not self._current_user:
		# 	raise ValueError("Сначала выполните login")

		return self._rates_service.get_rate_pair(from_v, to)

	@log_action("DEPOSIT", verbose=True)
	def deposit(self, amount):
		if not self._current_user:
			raise ValueError("Сначала нужно зарегистрироваться")

		portfolio = self._current_portfolio
		if not portfolio:
			raise RuntimeError("Портфель пользователя не загружен")

		# TODO: точно стоит менять на self._base_currency?
		usd_wallet = portfolio.get_or_create_wallet(self._base_currency)

		before = usd_wallet.balance
		usd_wallet.deposit(amount)
		after = usd_wallet.balance

		self._save_portfolio(portfolio)

		# TODO: точно стоит менять на self._base_currency?
		return {
			"currency": self._base_currency,
			"before": before,
			"after": after,
			"amount": amount,
		}

	def _save_portfolio(self, portfolio: Portfolio):
			portfolios = self._load(self._portfolio_dir)

			data = portfolio.to_dict()

			for i, p in enumerate(portfolios):
				if p["user_id"] == portfolio.user.user_id:
					portfolios[i] = data
					break
			else:
				portfolios.append(data)

			self._save(self._portfolio_dir, portfolios)

# TODO: все таки в buy/sell/deposit использовать "USD", base_currency из settings или