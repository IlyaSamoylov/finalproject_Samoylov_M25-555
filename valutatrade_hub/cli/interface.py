from valutatrade_hub.core.exceptions import ValutaTradeError
from valutatrade_hub.core.usecases import UseCases
from valutatrade_hub.infra.settings import SettingsLoader


class ValutatradeCLI:
	"""
		CLI-интерфейс для взаимодействия с ValutaTrade Hub.

		Отвечает за:
		- считывание ввода с консоли
		- валидацию аргументов
		- вызов соответствующих команд UseCases
		- перехват доменных исключений и вывод сообщений пользователю.
	"""
	def __init__(self, usecases: UseCases):
		"""
		Инициализация CLI
		Args:
			usecases (UseCases): cлой бизнес логики приложения
		"""
		self._usecases = usecases
		self._running = True
		self._settings = SettingsLoader()
		self._base_currency = self._settings.get("default_base_currency")

	def print_help(self):
		"""
		Справка по доступным командам
		"""
		helps = {
			"register": "register --username <username> --password <password>",
			"login": "login --username <username> --password <password>",
			"buy": "buy --currency <currency> --amount <amount>",
			"sell": "sell --currency <currency> --amount <amount>",
			"show-portfolio": f"show-portfolio [--base <base> = {self._base_currency}]",
			"get-rate": "get-rate --from <from currency> --to <to currency>",
			"update-rates": "update-rates [--source <coingecko | exchangerate>]",
			"show-rates": "show-rates --currency <str> --top <int> [--base <str>]",
			"deposit": "deposit --amount",
			"logout": "logout",
			"whoami": "whoami",
			"справка": "help [--command <command>]",
			"Закончить работу": "exit"
		}
		print("Доступные команды:")
		for name, example in helps.items():
			print(f" {name:15} → {example}")

	@staticmethod
	def _parse_cmd() -> tuple[str, dict[str, str]]:
		"""
		Cчитывает и разбивает ввод с консоли на команду, аргументы и параметры
		Returns:
			tuple[str, dict[str, str]]: команда и словарь аргументов.
		"""
		raw = input(">").strip()
		if not raw:
			return "", {}

		parts = raw.split()
		command = parts[0]

		params = {}
		i = 1
		while i < len(parts):
			if not parts[i].startswith("--"):
				raise ValueError("Аргументы должны начинаться с '--'")
			key = parts[i][2:]
			if i + 1 >= len(parts):
				raise ValueError(f"Не указано значение для параметра --{key}")
			params[key] = parts[i + 1]
			i += 2

		return command, params

	@staticmethod
	def _validate_amount(params: dict) -> float:
		"""
		Валидирует и возвращает amount как число
		Args:
			params (dict): словарь аргументов команды
		Returns:
			float: значение amount
		"""
		try:
			return float(params["amount"])
		except ValueError:
			raise ValueError("Параметр --amount должен быть числом")

	def _require_params(self, params: dict, required: list[str]):

		"""
		Проверяет наличие обязательных аргументов команды

		Args:
			params (dict): переданные аргументы команды
			required (list[str]): cписок обязательных параметров
		"""
		missing = [name for name in required if not params.get(name)]
		if missing:
			args = ', '.join(f"--{m}" for m in missing)
			raise ValueError(f"Отсутствуют обязательные аргументы: {args}")

	def run(self):
		"""
		Запускает основной цикл CLI.

		Обрабатывает пользовательский ввод, вызывает методы UseCases и выводит результат
		"""
		print("Добро пожаловать")
		self.print_help()
		while self._running:
			try:
				command, params = self._parse_cmd()

				match command:
					case "register":
						self._require_params(params, ["username", "password"])
						u_name = params.get('username')
						pword = params.get('password')
						self._usecases.register(username=u_name, password=pword)
						print(f"В подарок за регистрацию вы получаете стартовый баланс "
							f"100 {self._base_currency}.",
							f"Для пополнения баланса в базовой валюте "
							f"({self._base_currency} используйте команду deposit")

					case "login":
						self._require_params(params, ["username", "password"])
						u_name = params.get('username')
						pword = params.get('password')
						self._usecases.login(username=u_name, password=pword)

					case "show-portfolio":

						base = params.get("base") or self._base_currency

						items, total = self._usecases.show_portfolio(base)

						print(f"Портфель (база: {base}):")
						for code, balance, converted in items:
							print(f"- {code}: {balance:.4f} → {converted:.2f} {base}")
						print("-" * 30)
						print(f"ИТОГО: {total:.2f} {base}")

					case "buy":

						self._require_params(params, ["currency", "amount"])
						currency = params.get("currency")
						amount = self._validate_amount(params)
						result = self._usecases.buy(currency=currency, amount=amount)

						print(f"Покупка выполнена: {amount:.4f} {currency} по курсу "
								f"{result['rate']:.2f} USD/{currency} \n"
								f"Изменения в портфеле: \n"
							f"- {currency}: было {result['before']:.4f} → " 
							f"стало {result['after']:.4f} \n"
						f"Оценочная стоимость покупки: {result['cost']:.2f} USD")

					case "sell":
						self._require_params(params, ["currency", "amount"])
						currency = params.get("currency")
						amount = self._validate_amount(params)
						result = self._usecases.sell(currency=currency, amount=amount)

						print(f"Продажа выполнена: {amount:.4f} {currency} по курсу "
								f"{result['rate']:.2f} USD/{currency} \n"
								f"Изменения в портфеле: \n"
							f"- {currency}: было {result['before']:.4f} → " 
							f"стало {result['after']:.4f} \n"
						f"Оценочная выручка: {result['cost']:.2f} USD")

					case "get-rate":
						self._require_params(params, ["from", "to"])
						from_v, to = params.get("from"), params.get("to")
						result = self._usecases.get_rate(from_v=from_v, to=to)

						updated = result["updated_at"].strftime("%Y-%m-%d %H:%M:%S")

						print(f"Курс {from_v}→{to}: {result['rate']:.8f} "
							f"(обновлено: {updated})")
						print(f"Обратный курс {to}→{from_v}: "
								f"{result['reverse_rate']:.8f}")

					case "update-rates":
						source = params.get("source")
						self._usecases.update_rates(source=source)
						print("Обновление курсов завершено. Подробности см. в логах.")

					case "show-rates":
						currency = params.get("currency")

						top = params.get("top")
						if top is not None:
							try:
								top = int(top)
							except ValueError:
								raise ValueError("--top должен быть целым числом")

						base = params.get("base")

						rates = self._usecases.show_rates(currency, top, base)

						for line in rates:
							print(line)

					case "deposit":
						self._require_params(params, ["amount"])
						amount = self._validate_amount(params)
						result = self._usecases.deposit(amount)

						print(
							f"Баланс пополнен на {result['amount']:.2f} "
							f"{self._base_currency}\n"
							f"Было: {result['before']:.2f} {self._base_currency}\n"
							f"Стало: {result['after']:.2f} {self._base_currency}"
						)

					case "logout":
						self._usecases.logout()

					case "whoami":
						print(self._usecases.whoami())

					case "help":
						self.print_help()

					case "exit":
						self._running = False

					case _:
						print("Неизвестная команда")

			except ValutaTradeError as e:
				print(e)
			except ValueError as e:
				print(e)
			except IndexError:
				print("Вводите сначала имя переменной с \"--\", потом значение")
			except Exception as e:
				print(f"Неожиданная ошибка: \n{e}")