from valutatrade_hub.core.usecases import UseCases
from valutatrade_hub.core.utils import init_data_files

class ValutatradeCLI:
	def __init__(self, usecases: UseCases):
		self._usecases = usecases
		self._running = True

	def print_help(self, command=None):
		helps = {
			"register": "register --username <username> --password <password>",
			"login": "login --username <username> --password <password>",
			"buy": "buy --currency <currency> --amount <amount>",
			"sell": "sell --currency <currency> --amount <amount>",
			"show-portfolio": "show-portfolio [--base <base> = USD]",
			"get-rate": "get-rate --from <from currency> --to <to currency>",
			"справка": "help [--command <command>]",
			"Закончить работу": "exit"
		}
		if command and command in helps:
			print(helps[command])
		else:
			print("Доступные команды:")
			for name, example in helps.items():
				print(f"  {name:15} → {example}")

	@staticmethod
	def _parse_cmd():
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
	def _validate_amount(params: dict):
		try:
			return float(params["amount"])
		except ValueError:
			raise ValueError("Параметр --amount должен быть числом")

	def _require_params(self, params: dict, required: list[str]):
		missing = [name for name in required if not params.get(name)]
		if missing:
			args = ', '.join(f"--{m}" for m in missing)
			raise ValueError(f"Отсутствуют обязательные аргументы: {args}")

	def run(self):
		init_data_files()
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

					case "login":
						self._require_params(params, ["username", "password"])
						u_name = params.get('username')
						pword = params.get('password')
						self._usecases.login(username=u_name, password=pword)

					case "show-portfolio":
						# TODO: base не передается, потому и не валидируется
						# вместо None будет автоматически возвращать "USD"
						base = params.get("base") or "USD"

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
						self._usecases.buy(currency=currency, amount=amount)

					case "sell":
						self._require_params(params, ["currency", "amount"])
						currency = params.get("currency")
						amount = self._validate_amount(params)
						self._usecases.sell(currency=currency, amount=amount)

					case "get-rate":
						self._require_params(params, ["from", "to"])
						from_v, to = params.get("from"), params.get("to")
						self._usecases.get_rate(from_v=from_v, to=to)

					case "help":
						self.print_help(params.get("command"))

					case "exit":
						self._running = False

					case _:
						print("Неизвестная команда")


			# except TypeError:
			# 	print("Проверьте правильность и количество параметров. Можете обратиться к"
			# 	      " справке, вызвав help для полной справки или help --command <command>
			# 	      " для справки по отдельной команде")
			except ValueError as e:
				print(e)
			except IndexError:
				print("Вводите сначала имя переменной с \"--\", потом значение")
			except Exception as e:
				print(f"Неожиданная ошибка: \n{e}")

# TODO: сделать что-то с raise ошибок, просто обернуть все в try...except не кажется правильным,
#  как вариант: написать пользовательские ошибки и вставить их, потому что иначе ValueError
#  будет выбрасываться и не понятно, почему - то ли amount нет, то ли обязательных аргументов нет

# TODO: _require_params проверяет только то, есть ли обязательные аргументы. Неплохо было бы
#  проверять, нет ли лишних. Это либо отдельный метод, либо объединить эти два в один
