# main.py
# Entrypoint do Fizzy Bee. Inicializa o logger e dispara o Flet app em modo asyncio.

import flet as ft

from core.logger import setup_logger
from ui.app import main as app_main


def main() -> None:
    setup_logger()
    ft.run(app_main)


if __name__ == "__main__":
    main()
