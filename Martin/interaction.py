from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from .bot import Martin


class MartinInteraction(discord.Interaction):
    client: "Martin"


async def response_or_followup(
    interaction: "MartinInteraction", *args, **kwargs
) -> discord.InteractionMessage:
    if interaction.response.is_done():
        return await interaction.followup.send(*args, **kwargs)
    else:
        await interaction.response.send_message(*args, **kwargs)
        return await interaction.original_response()
