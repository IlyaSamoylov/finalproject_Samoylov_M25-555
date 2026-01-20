from __future__ import annotations
from abc import ABC, abstractmethod

from exceptions import CurrencyNotFoundError

class Currency(ABC):
	def __init__(self, name: str, code: str):
		if not name:
			raise ValueError("Название валюты не может быть пустым")

		if (not isinstance(code, str) or not code.isupper() or not 2 <= len(code.strip()) <= 5
				or " " in code):
			raise ValueError("Несоответствующий формат валюты.")

		self.name = name
		self.code = code

	@abstractmethod
	def get_display_info(self):
		pass

class FiatCurrency(Currency):
	def __init__(self, name, code,  issuing_country: str):
		if not issuing_country or not isinstance(issuing_country, str):
			raise ValueError("Страна должна быть непустой строкой")

		super().__init__(name, code)
		self.issuing_country =  issuing_country

	def get_display_info(self):
		return f"[FIAT] {self.code} - {self.name} (Issuing: {self.issuing_country})"

class CryptoCurrency(Currency):
	def __init__(self, name: str, code: str, algorithm: str, market_cap: float):
		# валидация?
		super().__init__(name, code)
		self.algorithm = algorithm
		self.market_cap = market_cap

	def get_display_info(self):
		# Краткая капитализация это MCAP? Где ее взять?
		return f"[CRYPTO] {self.code} - {self.name} (Algo: {self.algorithm}, MCAP: {self.market_cap:.2e})"

# Реестр валют
# TODO: сейчас рубль во всем проекте есть рубль. Если добавится состояние или нужны будут разные сигнатуры и пр
#  добавлю lambda: Currency
_CURRENCY_REGISTRY = {
	"RUB": FiatCurrency("Ruble", "RUB", "Russia"),
	"CNY": FiatCurrency("Chinese Yuan", "CNY", "China"),
    "USD": FiatCurrency("US Dollar", "USD", "United States"),
	"EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
    "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
	"ETH": CryptoCurrency("Ethereum", "ETH", "Ethash", 3.7e11)
}

def get_currency(code: str) -> Currency:
	if not isinstance(code, str):
		raise TypeError("ISO-Код валюты должен быть строкой")
	try:
		return _CURRENCY_REGISTRY[code]
	except KeyError:
		raise CurrencyNotFoundError(code)



