import logging
from datetime import datetime, timezone
from typing import Iterable, Dict, List

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.api_clients import BaseApiClient
from valutatrade_hub.parser_service.storage import RatesStorage

logger = logging.getLogger("valutatrade")

class RatesUpdater:
	def __init__(self, clients: Iterable[BaseApiClient], storage: RatesStorage):
		self._clients = clients
		self._storage = storage

	def run_update(self) -> None:
		logger.info("Запуск обновления курсов")

		combined_rates: Dict[str, Dict[str, object]] = {}
		history_records: List[Dict[str, object]] = []

		timestamp = datetime.now(timezone.utc).isoformat()

		for client in self._clients:
			client_name = client.__class__.__name__
			logger.info("Запрос курсов у %s", client_name)

			try:
				rates = client.fetch_rates()
				logger.info(
					"Успешно получены данные от %s (%d пар)",
					client_name,	len(rates),
				)

				for pair, obj in rates.items():
					combined_rates[pair] = {
						"rate": obj["rate"],
						"updated_at": timestamp,
						"source": getattr(client, "SOURCE", client_name),
					}

				history_records.extend(
					self._build_history_records(
						rates=rates,
						source=getattr(client, "SOURCE", client_name),
						timestamp=timestamp,
					)
				)

			except ApiRequestError as e:
				logger.error("Ошибка при работе с %s: %s",client_name, e)

		if not combined_rates:
			logger.warning("Не удалось получить курсы ни от одного источника")
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

		logger.info(
			"Обновление завершено: %d пар, %d записей истории",
			len(combined_rates),
			len(history_records),
		)

	@staticmethod
	def _build_history_records(
			rates: Dict[str, Dict[str, object]],
			source: str,
			timestamp: str,
			) -> List[Dict[str, object]]:

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
