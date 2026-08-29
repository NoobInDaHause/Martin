from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from .bot import Martin


class MartinContext(commands.Context):
    bot: "Martin"
