import os
from dataclasses import dataclass
from typing import ClassVar

@dataclass
class ParserConfig:
	# Ключ загружается из переменной окружения
	EXCHANGERATE_API_KEY: str = os.getenv("EXCHANGERATE_API_KEY")

	# Эндпоинты
	COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
	EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

	# Списки валют
	BASE_CURRENCY: str = "USD"
	FIAT_CURRENCIES: tuple = ("EUR", "GBP", "RUB", "CNY")
	CRYPTO_CURRENCIES: tuple = ("BTC", "ETH", "SOL")
	CRYPTO_ID_MAP: ClassVar[dict[str, str]] = {
	    "BTC": "bitcoin",
	    "ETH": "ethereum",
	    "SOL": "solana",
	}

	# Пути
	RATES_FILE_PATH: str = "data/rates.json"
	HISTORY_FILE_PATH: str = "data/exchange_rates.json"

	# Сетевые параметры
	REQUEST_TIMEOUT: int = 10

	def __post_init__(self):
		if not self.EXCHANGERATE_API_KEY:
			raise RuntimeError("API-ключ не установлен.")