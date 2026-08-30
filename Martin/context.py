from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from .bot import Martin


class MartinContext(commands.Context):
    bot: "Martin"

    async def send_help(self, *args):
        if not args:
            args = (self.command,)
        return await super().send_help(*args)
