class ValutaTradeError(Exception):
	"""
	Базовое исключение для ValutaTrade
	"""
	pass

class InsufficientFundsError(ValutaTradeError):
	"""
	Недостаточно средств
	"""
	def __init__(self, available :float, code: str, required: float):
		super().__init__(f"Недостаточно средств: доступно {available:.8f} {code}, "
							f"требуется {required:.8f} {code}")

		self.available = available
		self.code = code
		self.req_funds = required

class CurrencyNotFoundError(ValutaTradeError):
	"""
	Неизвестная валюта
	"""
	def __init__(self, code:str):
		super().__init__(f"Неизвестная валюта '{code}'")
		self.code = code

class ApiRequestError(ValutaTradeError):
	"""
	Ошибка при обращении к внешнему API
	"""
	def __init__(self, reason: str):
		super().__init__(f"Ошибка при обращении к внешнему API: {reason}")
		self.reason = reason

class WalletNotFoundError(ValutaTradeError):
	"""
	Отсутствует кошелек
	"""
	def __init__(self, currency: str):
		super().__init__(f"Отсутствует кошелек '{currency}'")
		self.currency = currency
