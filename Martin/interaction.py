from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from .bot import Martin


class MartinInteraction(discord.Interaction["Martin"]):
    async def response_or_followup(self, *args, **kwargs) -> discord.InteractionMessage:
        pass # This is just for type annotaions


async def response_or_followup(
    self: "MartinInteraction", *args, **kwargs
) -> discord.InteractionMessage:
    if self.response.is_done():
        return await self.followup.send(*args, **kwargs)
    await self.response.send_message(*args, **kwargs)
    return await self.original_response()
