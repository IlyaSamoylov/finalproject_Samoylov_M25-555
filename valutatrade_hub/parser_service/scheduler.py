"""
Планировщик периодического обновления курсов валют.

Использует RatesUpdater для обновления данных с заданным интервалом.
Логирует запуск, паузы и критические ошибки.
"""

import logging
import time

from valutatrade_hub.parser_service.updater import RatesUpdater

logger = logging.getLogger("valutatrade")


class RatesScheduler:
	"""
	Планировщик периодического вызова RatesUpdater.
    """

	def __init__(self, updater: RatesUpdater, interval_seconds: int):
		"""
		Инициализация планировщика периодического фонового обновления курсов
		Args:
			updater (RatesUpdater): объект, выполняющий обновление курсов.
			interval_seconds (int): интервал обновления в секундах.

		Атрибут running (bool): флаг состояния планировщика.
		"""

		self._updater = updater
		self._interval = interval_seconds
		self._running = False

	def start(self) -> None:
		"""
			Запуск цикла планировщика.

			Логирует начало работы, время до следующего обновления.
			Перехватывает KeyboardInterrupt для корректной остановки.
			Запущен в main как daemon - при выходе из приложения через exit
			автоматически остановится вместе с основным потоком.
		"""
		logger.info("Планировщик запущен, интервал обновления: %d секунд",
			self._interval)
		self._running = True

		try:
			while self._running:
				start_ts = time.monotonic()

				self._updater.run_update(trigger='RatesScheduler')

				elapsed = time.monotonic() - start_ts
				sleep_time = max(0, self._interval - elapsed)

				logger.info("Следующее обновление через %.1f секунд",
					sleep_time)

				time.sleep(sleep_time)

		except KeyboardInterrupt:
			logger.info("Планировщик остановлен пользователем")

		except Exception as exc:
			logger.exception("Критическая ошибка планировщика: %s", exc)
			raise

	def stop(self) -> None:
		"""
		Останавливает цикл планировщика.
		"""
		self._running = False
