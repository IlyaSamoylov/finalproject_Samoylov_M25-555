from __future__ import annotations

from abc import ABC, abstractmethod

from valutatrade_hub.core.exceptions import CurrencyNotFoundError


class Currency(ABC):
	"""
	Базовый класс валюты.
	"""
	def __init__(self, name: str, code: str):
		if not name:
			raise ValueError("Название валюты не может быть пустым")

		if (not isinstance(code, str) or not code.isupper()
									or not 2 <= len(code.strip()) <= 5 or " " in code):
			raise ValueError("Несоответствующий формат валюты.")

		self.name = name
		self.code = code

	@abstractmethod
	def get_display_info(self):
		"""
		Возвращает строку для отображения валюты пользователю
		Returns:
			str: строковое представление валюты
		"""
		pass

class FiatCurrency(Currency):
	"""
	Класс фиатной валюты
	"""
	def __init__(self, name, code,  issuing_country: str):
		if not issuing_country or not isinstance(issuing_country, str):
			raise ValueError("Страна должна быть непустой строкой")

		super().__init__(name, code)
		self.issuing_country = issuing_country

	def get_display_info(self):
		return f"[FIAT] {self.code} - {self.name} (Issuing: {self.issuing_country})"

class CryptoCurrency(Currency):
	"""
	Класс криптовалюты
	"""
	def __init__(self, name: str, code: str, algorithm: str, market_cap: float):
		super().__init__(name, code)

		if not algorithm or not isinstance(algorithm, str):
			raise ValueError("Алгоритм должен быть непустой строкой")

		if not isinstance(market_cap, (int, float)) or market_cap <= 0:
			raise ValueError("Некорректная капитализация")

		self.algorithm = algorithm
		self.market_cap = market_cap

	def get_display_info(self):
		return (f"[CRYPTO] {self.code} - {self.name} (Algo: {self.algorithm}, "
				f"MCAP: {self.market_cap:.2e})")

# Реестр валют
_CURRENCY_REGISTRY = {
	"RUB": FiatCurrency("Ruble", "RUB", "Russia"),
	"CNY": FiatCurrency("Chinese Yuan", "CNY", "China"),
    "USD": FiatCurrency("US Dollar", "USD", "United States"),
	"EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
    "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
	"ETH": CryptoCurrency("Ethereum", "ETH", "Ethash", 3.7e11),
	"SOL": CryptoCurrency("Solana", "SOL", "Proof of History", 12e9)
}

def get_currency(code: str) -> Currency:
	"""
	Возвращает объект валюты по ее коду

	Args:
		code (str): код валюты
	Returns:
		Currency: экземпляр класса валюты
	"""
	if not isinstance(code, str):
		raise TypeError("ISO-Код валюты должен быть строкой")
	try:
		return _CURRENCY_REGISTRY[code]
	except KeyError:
		raise CurrencyNotFoundError(code)

def get_fiat_currencies() -> list[str]:
	"""
	Вернуть список кодов фиатных валют

	Returns:
		list[str]: список строк - кодов фиантых валют.
	"""
	return [code for (code, cls) in _CURRENCY_REGISTRY.items()
			if isinstance(cls, FiatCurrency)]

def get_crypto_currencies() -> list[str]:
	"""
	Вернуть список кодов криптовалют

	Returns:
		list[str]: список строк - кодов криптовалют.
	"""
	return [code for (code, cls) in _CURRENCY_REGISTRY.items()
			if isinstance(cls, CryptoCurrency)]



