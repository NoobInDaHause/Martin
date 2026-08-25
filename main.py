import logging
import os
from pathlib import Path

from dotenv import find_dotenv, load_dotenv

from Martin import Martin, Settings


def run_bot() -> None:
    logging.basicConfig(
        level=logging.INFO,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(Path(__file__).parents[1] / "logs.log", "w"),
        ],
        format="[{asctime}] [{levelname}] {name:<15}: {message}",
        datefmt="%Y-%m-%d %H:%M:%S",
        style="{",
    )

    load_dotenv(find_dotenv(raise_error_if_not_found=True))

    settings = Settings.initialize()
    bot = Martin(settings)
    bot.run(token=os.getenv("TOKEN"), log_handler=None)
    raise SystemExit(bot.exit_code)


if __name__ == "__main__":
    run_bot()
