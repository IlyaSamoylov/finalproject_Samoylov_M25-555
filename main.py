#!/usr/bin/env python3
import threading

from valutatrade_hub.cli.interface import ValutatradeCLI
from valutatrade_hub.core.usecases import RatesService, UseCases
from valutatrade_hub.logging_config import setup_logging
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.scheduler import RatesScheduler
from valutatrade_hub.parser_service.storage import RatesStorage
from valutatrade_hub.parser_service.updater import RatesUpdater


def main():
    setup_logging()

    parser_config = ParserConfig()

    # updater для курсов
    clients = [CoinGeckoClient(parser_config), ExchangeRateApiClient(parser_config)]

    storage = RatesStorage(parser_config)
    updater = RatesUpdater(clients, storage)

    # scheduler периодически фоново обновляет курсы
    scheduler = RatesScheduler(updater, parser_config.RATES_UPDATE_INTERVAL)

    scheduler_thread = threading.Thread(target=scheduler.start, daemon=True,
                                        name="rates-scheduler")
    scheduler_thread.start()

    rates_service = RatesService()
    usecases = UseCases(rates_service)
    cli = ValutatradeCLI(usecases)
    cli.run()

if __name__ == "__main__":
    main()

