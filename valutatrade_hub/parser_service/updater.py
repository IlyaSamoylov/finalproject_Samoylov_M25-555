import logging
import threading
from datetime import datetime, timezone
from typing import Any, Iterable

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.api_clients import BaseApiClient
from valutatrade_hub.parser_service.storage import RatesStorage

logger = logging.getLogger("valutatrade")

class RatesUpdater:
	"""
	Сервис обновления курсов валют из внешних API.

	Опрашивает всех подключенных API-клиентов, объединяет полученные курсы и сохраняет
	актуальные данные в хранилища.
	"""
	def __init__(self, clients: Iterable[BaseApiClient], storage: RatesStorage):
		"""
		Инициализирует сервис обновления курсов

		Args:
			clients (Iterable[BaseApiClient]): набор API-клиентов
			storage (RatesStorage): класс для записи/получения данных из хранилища
			курсов и истории обновлений
		"""
		self._clients = clients
		self._storage = storage
		self._lock = threading.RLock()

	def run_update(self, trigger: str) -> None:
		"""
		Запуск истории обновления курсов валют.

		Опрашивает все источники, объединяет данные, сохраняет актуальные курсы и
		историю обновлений

		Args:
			trigger (str): источник, запустивший обновление - CLI/Scheduler
		"""
		with self._lock:
			log = logging.LoggerAdapter(logger,{"trigger": trigger})

			log.info("Запуск обновления курсов")

			combined_rates: dict[str, dict[str, Any]] = {}
			history_records: list[dict[str, Any]] = []

			timestamp = datetime.now(timezone.utc).isoformat()

			for client in self._clients:
				client_name = client.__class__.__name__
				log.info("Запрос курсов у %s", client_name)

				try:
					rates = client.fetch_rates()
					log.info("Успешно получены данные от %s (%d пар)",
								client_name,	len(rates))

					for pair, obj in rates.items():
						combined_rates[pair] = {
							"rate": obj["rate"],
							"updated_at": timestamp,
							"source": getattr(client, "SOURCE", client_name)
						}

					history_records.extend(
						self._build_history_records(rates,
						getattr(client, "SOURCE", client_name), timestamp)
					)

				except ApiRequestError as e:
					log.error("Ошибка при работе с %s: %s",client_name, e)

			if not combined_rates:
				log.warning("Не удалось получить курсы ни от одного источника")
				return

			existing = self._storage.load_rates()
			existing_pairs = existing.get("pairs", {})

			existing_pairs.update(combined_rates)

			result = {
				"pairs": existing_pairs,
				"last_refresh": timestamp,
			}
			self._storage.save_rates(result)

			if history_records:
				self._storage.append_history(history_records)

			log.info("Обновление завершено: %d пар, %d записей истории",
				len(combined_rates), len(history_records))

	@staticmethod
	def _build_history_records(rates: dict[str, dict[str, Any]], source: str,
											timestamp: str) -> list[dict[str, Any]]:
		"""
		Формирует запись истории курсов

		Args:
			rates (dict[str, dict[str, Any]]): словарь курсов от API-клиента
			source (str): имя источника курсов
			timestamp (str): время обновления

		Returns:
			Список словарей для записи в историю курсов
		"""
		records = []

		for pair, obj in rates.items():
			from_currency, to_currency = pair.split("_")

			records.append({
				"id": f"{pair}_{timestamp}",
				"from_currency": from_currency,
				"to_currency": to_currency,
				"rate": obj["rate"],
				"timestamp": timestamp,
				"source": source,
				"meta": obj.get("meta", {})
			})

		return records
