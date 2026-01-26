from __future__ import annotations

from abc import ABC, abstractmethod
import requests
from requests.exceptions import RequestException
from typing import Type
import time

from typing import Dict
from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig


class BaseApiClient(ABC):
	"""
	Базовый интерфейс для всех API-клиентов.
    Каждый клиент обязан вернуть курсы
    в стандартизированном формате: {"BTC_USD": rate, ...}
	"""

	def __init__(self, config: ParserConfig):
		self._config = config

	@abstractmethod
	def fetch_rates(self) -> dict:
		"""
		Получить курсы валют.

		:return: словарь вида {"BTC_USD": 59337.21}
		:raises ApiRequestError: при любой ошибке API или сети
        """
		raise NotImplementedError


class CoinGeckoClient(BaseApiClient):
	SOURCE = "CoinGecko"
	def fetch_rates(self) -> dict[str, float]:
		ids = ",".join(self._config.CRYPTO_ID_MAP.values())
		vs_currency = self._config.BASE_CURRENCY.lower()

		params = {
			"ids": ids,
			"vs_currencies": vs_currency
		}

		start_time = time.monotonic()

		try:
			response = requests.get(
				self._config.COINGECKO_URL,
				params=params,
				timeout=self._config.REQUEST_TIMEOUT,
			)
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
				raise ApiRequestError(
					f"Ответ API CoinGecko не содержит данных: '{raw_id}'")

			price_info = data[raw_id]
			if vs_currency not in price_info:
				raise ApiRequestError(
					f"Ответ CoinGecko не содержит курс для  '{vs_currency}' - '{raw_id}'"
				)

			rate = price_info[vs_currency]
			if not isinstance(rate, (int, float)):
				raise ApiRequestError(f"Неправильный тип данных для {code}: {rate!r}")

			pair = f"{code}_{self._config.BASE_CURRENCY}"
			result[pair] = {
				"rate": float(rate),
				"meta": {
					"raw_id": raw_id,
					"request_ms": elapsed_ms,
					"status_code": response.status_code,
					"etag": response.headers.get("ETag"),
				},
			}

		return result


class ExchangeRateApiClient(BaseApiClient):
	SOURCE = "ExchangeRate-API"
	def fetch_rates(self) -> Dict[str, float]:
		if not self._config.EXCHANGERATE_API_KEY:
			raise ApiRequestError(
				"Не удалось получить API ключ"
			)

		url = (
			f"{self._config.EXCHANGERATE_API_URL}/{self._config.EXCHANGERATE_API_KEY}"
			f"/latest/{self._config.BASE_CURRENCY}")

		start_time = time.monotonic()

		try:
			response = requests.get(
				url,
				timeout=self._config.REQUEST_TIMEOUT,
			)
			response.raise_for_status()
		except RequestException as e:
			raise ApiRequestError(f"Ошибка при обращении к ExchangeRate-API: {e}")

		elapsed_ms = int((time.monotonic() - start_time) * 1000)

		try:
			data = response.json()
		except ValueError as e:
			raise ApiRequestError(
				"Неверный ответ ExchangeRate-API"
			)

		if data.get("result") != "success":
			error_type = data.get("error-type", "unknown")
			raise ApiRequestError(
				f"Ошибка при обращении к ExchangeRate-API: {error_type}"
			)

		rates_block = data.get("conversion_rates")
		if not isinstance(rates_block, dict):
			raise ApiRequestError(
				"Ответ ExchangeRate-API не содержит блока курсов"
			)

		result = {}

		for currency in self._config.FIAT_CURRENCIES:
			if currency not in rates_block:
				raise ApiRequestError(
					f"Курс '{currency}' не найден в ответе ExchangeRate-API"
				)

			rate = rates_block[currency]
			if not isinstance(rate, (int, float)):
				raise ApiRequestError(
					f"Неправильный тип курса для {currency}: {rate!r}"
				)

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

