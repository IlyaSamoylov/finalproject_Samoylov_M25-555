import datetime
import hashlib
import secrets

from valutatrade_hub.constants import PORTFOLIOS_DIR, RATES_DIR, USERS_DIR, VALUTA
from valutatrade_hub.core.utils import get_session, get_user, load, save, set_session
from valutatrade_hub.core.models import User, Wallet, Portfolio


# TODO: здесь, пока не напишем доступ к курсам через API или что там
class RatesService:
	@staticmethod
	def get_rate(from_: str, to: str) -> float:
		rates = load(RATES_DIR)
		if from_ != to and f"{from_}_{to}" not in rates:
			raise ValueError(f"Неизвестная валюта конвертации: {to}")
		return 1.0 if from_ == to else rates[f"{from_}_{to}"]["rate"]


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
		if currency not in wallets.keys():
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
			print("На кошельке недостаточно средств")
			return

		# в этот момент оно меняется по ссылкам и в списке portfolio_lst!!!
		user_wallets[currency]["balance"] -= amount

		save(PORTFOLIOS_DIR, portfolios_lst)

	def get_rate(from_v:str, to:str):
		if from_v not in VALUTA:
			print("Исходная валюта не существует")

		if to not in VALUTA:
			print("Итоговая валюта не существует")

		rate_dct = load(RATES_DIR)

		last_refresh_str = rate_dct["last_refresh"]
		last_refresh = datetime.datetime.fromisoformat(last_refresh_str)

		# last_refresh aware (UTC)
		if last_refresh.tzinfo is None:
			last_refresh = last_refresh.replace(tzinfo=datetime.UTC)

		current_time = datetime.datetime.now(datetime.UTC)

		if current_time - last_refresh < datetime.timedelta(minutes=5):
			print(f"Курс {from_v}->{to}: {rate_dct[f"{from_v}_{to}"]}, "
															f"(обновлен {last_refresh}")
		else:
			print("Нет данных и недоступен Parser ->")
			print(f"Курс {from_v}->{to} недоступен. Повторите позже")
