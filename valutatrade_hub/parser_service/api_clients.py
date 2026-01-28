from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Type

import requests
from requests.exceptions import RequestException

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig


class BaseApiClient(ABC):
	"""
	Базовый интерфейс для всех источников курсов по API.
    Клиенты возвращают курсы в стандартизированном формате:
    {"<curr1_curr2>":{"rate": float, "meta": dict}}
	"""

	def __init__(self, config: ParserConfig):
		self._config = config

	@abstractmethod
	def fetch_rates(self) -> dict:
		"""
		Получить курсы валют по API.

		Returns:
			dict: словарь курсов в стандартизированном виде
        """
		raise NotImplementedError


class CoinGeckoClient(BaseApiClient):
	"""
	API-клиент CoinGecko для получения курсов криптовалют
	"""

	SOURCE = "CoinGecko"

	def fetch_rates(self) -> dict[str, dict]:
		"""
		Получение курсов криптовалют от CoinGecko

		Returns:
			dict[str, dict]: словарь с курсами криптовалют от CoinGecko относительно
			базовой валюты
		"""
		ids = ",".join(self._config.CRYPTO_ID_MAP.values())
		vs_currency = self._config.BASE_CURRENCY.lower()

		params = {"ids": ids, "vs_currencies": vs_currency}

		start_time = time.monotonic()

		try:
			response = requests.get(self._config.COINGECKO_URL, params=params,
				timeout=self._config.REQUEST_TIMEOUT)
			response.raise_for_status()

		except RequestException as e:
			raise ApiRequestError(f"Ошибка при обращении к CoinGecko: {e}")

		elapsed_ms = int((time.monotonic() - start_time) * 1000)

		try:
			data = response.json()
		except ValueError as e:
			raise ApiRequestError("CoinGecko вернул неправильный JSON") from e

		result = {}

		for code, raw_id in self._config.CRYPTO_ID_MAP.items():
			if raw_id not in data:
				raise ApiRequestError(f"Ответ API CoinGecko не содержит данных:"
										f" '{raw_id}'")

			price_info = data[raw_id]
			if vs_currency not in price_info:
				raise ApiRequestError(f"Ответ CoinGecko не содержит курс для "
										f"'{vs_currency}' - '{raw_id}'")

			rate = price_info[vs_currency]
			if not isinstance(rate, (int, float)):
				raise ApiRequestError(f"Неправильный тип данных для {code}: {rate!r}"
										f" (type={type(rate).__name__})")

			pair = f"{code}_{self._config.BASE_CURRENCY}"
			result[pair] = {
				"rate": float(rate),
				"meta": {
					"raw_id": raw_id,
					"request_ms": elapsed_ms,
					"status_code": response.status_code,
					"etag": response.headers.get("ETag"),
				}
			}

		return result


class ExchangeRateApiClient(BaseApiClient):
	"""
	API-клиент ExchangeRate-API для получения курсов фиатных валют.
	"""

	SOURCE = "ExchangeRate-API"

	def fetch_rates(self) -> dict[str, float]:
		"""
		Получить курсы фиатных валют через ExchangeRate-API

		Returns:
			dict[str, float]: стандартизированный словарь курсов
		"""
		if not self._config.EXCHANGERATE_API_KEY:
			raise ApiRequestError("Не удалось получить API ключ")

		url = (
			f"{self._config.EXCHANGERATE_API_URL}/{self._config.EXCHANGERATE_API_KEY}"
			f"/latest/{self._config.BASE_CURRENCY}"
		)

		start_time = time.monotonic()

		try:
			response = requests.get(url, timeout=self._config.REQUEST_TIMEOUT)
			response.raise_for_status()
		except RequestException as e:
			raise ApiRequestError(f"Ошибка при обращении к ExchangeRate-API: {e}")

		elapsed_ms = int((time.monotonic() - start_time) * 1000)

		try:
			data = response.json()
		except ValueError:
			raise ApiRequestError("Неверный ответ ExchangeRate-API")

		if data.get("result") != "success":
			err = data.get("error-type", "unknown")
			raise ApiRequestError(f"Ошибка при обращении к ExchangeRate-API: {err}")

		rates_block = data.get("conversion_rates")
		if not isinstance(rates_block, dict):
			raise ApiRequestError("Ответ ExchangeRate-API не содержит блока курсов")

		result = {}

		for currency in self._config.FIAT_CURRENCIES:
			if currency not in rates_block:
				raise ApiRequestError(f"Курс '{currency}' не найден в ответе"
										f" ExchangeRate-API")

			rate = rates_block[currency]
			if not isinstance(rate, (int, float)):
				raise ApiRequestError(f"Неправильный тип курса для {currency}: "
										f"{rate!r} (type={type(rate).__name__})")

			pair = f"{currency}_{self._config.BASE_CURRENCY}"
			result[pair] = {
				"rate": rate,
				"meta": {
					"request_ms": elapsed_ms,
					"status_code": response.status_code,
					"etag": response.headers.get("ETag"),
				}
			}

		return result

# реестр источников
PARSER_CLIENT_REGISTRY: dict[str, Type[BaseApiClient]] = {
	"coingecko": CoinGeckoClient,
	"exchangerate": ExchangeRateApiClient,
}

