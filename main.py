#!/usr/bin/env python3
from valutatrade_hub.cli.interface import ValutatradeCLI
from valutatrade_hub.core.usecases import UseCases, RatesService
from valutatrade_hub.logging_config import setup_logging

def main():
    setup_logging()
    rates_service = RatesService()
    usecases = UseCases(rates_service) # TODO: добавлю аргументы, когда допишу сам класс, пока заглушка
    cli = ValutatradeCLI(usecases)
    cli.run()

if __name__ == "__main__":
    main()

