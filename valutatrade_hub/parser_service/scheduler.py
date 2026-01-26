import logging
import time

from updater import RatesUpdater

logger = logging.getLogger(__name__)


class RatesScheduler:
	def __init__(self, updater: RatesUpdater, interval_seconds: int):
		self._updater = updater
		self._interval = interval_seconds
		self._running = False

	def start(self) -> None:
		logger.info(
			"Планировщик запущен, интервал обновления: %d секунд",
			self._interval,
		)
		self._running = True

		try:
			while self._running:
				start_ts = time.monotonic()

				self._updater.run_update()

				elapsed = time.monotonic() - start_ts
				sleep_time = max(0, self._interval - elapsed)

				logger.info(
					"Следующее обновление через %.1f секунд",
					sleep_time,
				)

				time.sleep(sleep_time)

		except KeyboardInterrupt:
			logger.info("Планировщик остановлен пользователем")

		except Exception as exc:
			logger.exception(
				"Критическая ошибка планировщика: %s",
				exc,
			)
			raise

	def stop(self) -> None:
		self._running = False
