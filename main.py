#!/usr/bin/env python3
from valutatrade_hub.cli.interface import ValutatradeCLI
from valutatrade_hub.core.usecases import UseCases

def main():
    usecases = UseCases() # TODO: добавлю аргументы, когда допишу сам класс, пока заглушка
    cli = ValutatradeCLI(usecases)
    cli.run()

if __name__ == "__main__":
    main()

