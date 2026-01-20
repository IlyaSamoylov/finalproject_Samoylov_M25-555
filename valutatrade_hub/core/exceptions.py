# не совсем понимаю, зачем это пустое базовое родительское исключение, почему не начать просто
# сразу писать нужные нам и наследовать их от Exceptions?
class ValutaTradeError(Exception):
	pass

class InsufficientFundsError(ValutaTradeError):
	def __init__(self, available :float, code: str, req_funds: float):
		#  валидация здесь и в других исключениях нужна?
		super().__init__(f"Недостаточно средств: доступно {available:.8f} {code},"
		                 f"требуется {req_funds:.8f} {code}")

		# зачем нужно какое-то присваивание, если в super мы уже должны были отправить нужное сообщение?
		self.available = available
		self.code = code,
		self.req_funds = req_funds

class CurrencyNotFoundError(ValutaTradeError):
	def __init__(self, code:str):
		super().__init__(f"Неизвестная валюта {code}")
		self.code = code

class ApiRequestError(ValutaTradeError):
	def __init__(self, reason: str):
		super().__init__(f"Ошибка при обращении к внешнему API: {reason}")
		self.reason = reason

