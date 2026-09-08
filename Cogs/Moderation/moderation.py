import contextlib

import discord
from discord.ext import commands
from discord import app_commands

from .utils import get_auditlog_reason, get_dm_embed

from Martin import Martin, MartinInteraction
from Utilities.checks import bot_has_permissions, has_permissions


class Moderation(commands.GroupCog, group_name="moderation"):
    def __init__(self, bot: Martin):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="kick", description="Kick a member.")
    @bot_has_permissions(kick_members=True)
    @has_permissions(kick_members=True)
    @app_commands.describe(offender="The offending member that you want to kick.", reason="The optional reason for the kick.")
    async def moderation_kick(
        self, interaction: MartinInteraction, offender: discord.Member, reason: str = None
    ):
        if (offender.top_role >= interaction.user.top_role) and not await self.bot.is_owner(interaction.user):
            return await interaction.response_or_followup(
                content="You can not kick a member that has a role higher than you."
            )
        if (offender.top_role >= interaction.guild.me.top_role):
            return await interaction.response_or_followup()

        embed = get_dm_embed(interaction.user, interaction.guild, reason or "No reason was given.", "kick")
        with contextlib.suppress(discord.errors.Forbidden, discord.errors.HTTPException):
            await offender.send(embed=embed)
        await interaction.guild.kick(offender, reason=get_auditlog_reason(interaction.user, reason))
