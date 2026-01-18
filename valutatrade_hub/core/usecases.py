import datetime


from valutatrade_hub.constants import PORTFOLIOS_DIR, RATES_DIR, USERS_DIR
from valutatrade_hub.core.utils import load, save, set_session
from valutatrade_hub.core.models import User, Wallet, Portfolio


# TODO: здесь, пока не напишем доступ к курсам через API или что там
class RatesService:
	CACHE_TTL = datetime.timedelta(minutes=5)

	@staticmethod
	def get_rate(from_: str, to: str) -> float:
		rates = load(RATES_DIR)
		if from_ != to and f"{from_}_{to}" not in rates:
			raise ValueError(f"Неизвестная валюта конвертации: {to}")
		return 1.0 if from_ == to else rates[f"{from_}_{to}"]["rate"]

	@staticmethod
	def validate_currency(code: str):
		rates = load(RATES_DIR)
		known = set()

		for pair in rates:
			if "_" in pair:
				a, b = pair.split("_")
				known.update([a, b])

		if code not in known:
			raise ValueError(f"Неизвестная валюта '{code}'")

	def _load_rates(self) -> dict:
		return load(RATES_DIR)

	def is_cache_fresh(self, rates: dict) -> bool:
		last_refresh_str = rates.get("last_refresh")
		if not last_refresh_str:
			return False

		last_refresh = datetime.datetime.fromisoformat(last_refresh_str)
		if last_refresh.tzinfo is None:
			last_refresh = last_refresh.replace(tzinfo=datetime.UTC)

		return datetime.datetime.now(datetime.UTC) - last_refresh < self.CACHE_TTL

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

		rates = self._load_rates()

		if not self.is_cache_fresh(rates):
			raise RuntimeError("Курс недоступен: кеш устарел и Parser недоступен")

		key = f"{from_}_{to}"
		reverse_key = f"{to}_{from_}"

		if key not in rates or reverse_key not in rates:
			raise RuntimeError(f"Курс {from_}->{to} недоступен")

		updated_at = datetime.datetime.fromisoformat(rates["last_refresh"])

		return {
			"rate": rates[key]["rate"],
			"reverse_rate": rates[reverse_key]["rate"],
			"updated_at": updated_at,
		}



class UseCases:
	def __init__(self, rates_service: RatesService, current_user: User | None = None,
	             current_portfolio: Portfolio | None = None):
		self._rates_service = rates_service
		self._current_user = current_user
		self._current_portfolio = current_portfolio

	# TODO: переписать в вообще все, теперь с классами(
	def register(self, username:  str, password: str):
		# password и username валидируются при инициализации экземпляра класса User ниже

		# загрузка пользователей
		users_lst = load(USERS_DIR)
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
		save(USERS_DIR, users_lst)

		new_portfolio = Portfolio(new_user)
		portfolios_lst = load(PORTFOLIOS_DIR)
		if portfolios_lst is None:
			portfolios_lst = []

		portfolios_lst.append(new_portfolio.to_dict())
		save(PORTFOLIOS_DIR, portfolios_lst)

		# TODO: наверное лучше будет вернуть консоли сообщение для вывода на экран
		print(f"Пользователь '{username}' зарегистрирован (id={user_id}). "
				f"Войдите: login --username {username} --password", len(password)*"*")

	def login(self, username: str, password: str):

		users_lst = load(USERS_DIR)
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
	@staticmethod
	def _load_portfolio(user: User) -> Portfolio:
		raw_portfolios = load(PORTFOLIOS_DIR)

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


	def show_portfolio(self, base: str | None  = 'USD'):
		# TODO: где будет проверяться base? - наверное, где-то в Currency
		if not self._current_user:
			raise ValueError("Сначала выполните login")

		if not self._current_portfolio.wallets:
			raise ValueError(f"Портфель пуст")

		return self._current_portfolio.view(base, self._rates_service)

	def buy(self, currency: str, amount: float):

		if not self._current_user:
			raise ValueError("Сначала нужно зарегистрироваться")

		# amount уже валидируется в CLI
		if amount <= 0:
			raise ValueError("'amount' должен быть положительным числом")

		# валидация валюты сейчас - ответственность курсов
		self._rates_service.validate_currency(code=currency)

		portfolio = self._current_portfolio
		if not portfolio:
			raise RuntimeError("Портфель пользователя не загружен")

		wallet = portfolio.get_or_create_wallet(currency)

		before = wallet.balance
		wallet.deposit(amount)
		after = wallet.balance

		# расчетная стоимость
		rate = self._rates_service.get_rate(currency, "USD")
		cost = amount * rate

		self._save_portfolio(portfolio)

		return {
			"currency": currency,
			"before": before,
			"after": after,
			"rate": rate,
			"cost": cost,
		}

	def sell(self, currency:str, amount:float):
		if not self._current_user:
			raise ValueError("Сначала нужно зарегистрироваться")

		if amount <= 0:
			raise ValueError("'amount' должен быть положительным числом")

		# валидация валюты сейчас - ответственность курсов
		self._rates_service.validate_currency(code=currency)

		portfolio = self._current_portfolio
		if not portfolio:
			raise RuntimeError("Портфель пользователя не загружен")

		if not portfolio.has_wallet(currency):
			raise ValueError(f"У вас нет кошелька {currency}. Добавьте валюту: "
			                 f"она создаётся автоматически при первой покупке.")

		wallet = portfolio.get_wallet(currency)

		before = wallet.balance
		wallet.withdraw(amount)
		after = wallet.balance

		# расчетная стоимость
		rate = self._rates_service.get_rate(currency, "USD")
		cost = amount * rate

		self._save_portfolio(portfolio)

		return {
			"currency": currency,
			"before": before,
			"after": after,
			"rate": rate,
			"cost": cost,
		}

	def get_rate(self, from_v:str, to:str):

		if not self._current_user:
			raise ValueError("Сначала выполните login")

		return self._rates_service.get_rate_pair(from_v, to)

	def _save_portfolio(self, portfolio: Portfolio):
		portfolios = load(PORTFOLIOS_DIR)

		data = portfolio.to_dict()

		for i, p in enumerate(portfolios):
			if p["user_id"] == portfolio.user.user_id:
				portfolios[i] = data
				break
		else:
			portfolios.append(data)

		save(PORTFOLIOS_DIR, portfolios)
