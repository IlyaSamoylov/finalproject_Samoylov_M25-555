import os
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from valutatrade_hub.core.currencies import get_crypto_currencies, get_fiat_currencies
from valutatrade_hub.infra.settings import SettingsLoader

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