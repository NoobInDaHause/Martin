from typing import TYPE_CHECKING, Any

from discord.ext import commands

if TYPE_CHECKING:
    from .bot import Martin


class MartinContext(commands.Context):
    bot: "Martin"

    async def send_help(self, *args: Any) -> Any:
        if not args:
            args = [self.command]
        return await super().send_help(*args)
