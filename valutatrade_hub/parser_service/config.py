"""
Конфигурация параметров парсеров и внешних API.

Содержит:
- URL внешних сервисов;
- API-ключи;
- списки поддерживаемых валют;
- пути к файлам данных;
- сетевые и временные параметры.
"""

import os
from dataclasses import dataclass
from typing import ClassVar
from valutatrade_hub.infra.settings import SettingsLoader
from pathlib import Path
from valutatrade_hub.core.currencies import get_fiat_currencies, get_crypto_currencies

settings = SettingsLoader()

@dataclass
class ParserConfig:
	"""
	    Конфигурация сервисов получения валютных курсов.
    """
	# API ключ загружается из переменной окружения
	EXCHANGERATE_API_KEY: str = os.getenv("EXCHANGERATE_API_KEY")

	# эндпоинты
	COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
	EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

	# списки валют
	BASE_CURRENCY: str = settings.get("default_base_currency", "USD")
	FIAT_CURRENCIES = get_fiat_currencies()
	CRYPTO_CURRENCIES = get_crypto_currencies()
	CRYPTO_ID_MAP: ClassVar[dict[str, str]] = {
	    "BTC": "bitcoin",
	    "ETH": "ethereum",
	    "SOL": "solana",
	}

	# пути
	BASE_DIR = Path(settings.get("data_dir"))
	RATES_FILE_PATH = BASE_DIR / "rates.json"
	HISTORY_FILE_PATH = BASE_DIR / "exchange_rates.json"

	# сетевые параметры
	REQUEST_TIMEOUT: int = 10

	def __post_init__(self):
		"""
		Валидирует обязательные параметры конфигурации
		:return:
		"""
		if not self.EXCHANGERATE_API_KEY:
			raise RuntimeError("API-ключ не установлен.")

	# частота обновления, с
	RATES_UPDATE_INTERVAL = 150