import asyncio
import logging
import os
from pathlib import Path

import discord
from dotenv import find_dotenv, load_dotenv

from Martin import Martin, Settings
from Martin.interaction import response_or_followup


def setup_lopgging():
    logging.basicConfig(
        level=logging.INFO,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(Path(__file__).parent / "logs.log", "w"),
        ],
        format="[{asctime}] [{levelname}] {name:<20}: {message}",
        datefmt="%Y-%m-%d %H:%M:%S",
        style="{",
    )


async def run_bot() -> None:
    setup_lopgging()

    load_dotenv(find_dotenv(raise_error_if_not_found=True))

    discord.Interaction.response_or_followup = response_or_followup  # Dirty way to add custom functions but it works and does its job

    settings = Settings.initialize()
    async with Martin(settings) as bot:
        await bot.start(token=os.getenv("TOKEN"))
        return bot.exit_code


if __name__ == "__main__":
    exit_code = asyncio.run(run_bot())
    raise SystemExit(exit_code)
