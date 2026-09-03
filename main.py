import logging
import os
from pathlib import Path

import discord
from dotenv import find_dotenv, load_dotenv

from Martin import Martin, Settings
from Martin.interaction import response_or_followup


def run_bot() -> None:
    from discord.ext import commands
    logging.basicConfig(
        level=logging.INFO,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(Path(__file__).parent / "logs.log", "w"),
        ],
        format="[{asctime}] [{levelname}] {name:<15}: {message}",
        datefmt="%Y-%m-%d %H:%M:%S",
        style="{",
    )

    load_dotenv(find_dotenv(raise_error_if_not_found=True))
    
    discord.Interaction.response_or_followup = response_or_followup
    settings = Settings.initialize()
    bot = Martin(settings)

    @bot.command(name="sync")
    @commands.is_owner()
    async def slash_sync(ctx):
        await bot.tree.sync()
        await ctx.send("Done.")

    bot.run(token=os.getenv("TOKEN"), log_handler=None)
    raise SystemExit(bot.exit_code)


if __name__ == "__main__":
    run_bot()
