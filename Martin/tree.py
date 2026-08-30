import discord

from .interaction import MartinInteraction


class MartinTree(discord.app_commands.CommandTree):
    async def _call(self, interaction: discord.Interaction):
        interaction.__class__ = MartinInteraction
        return await super()._call(interaction)
