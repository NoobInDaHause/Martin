from typing import Union
import contextlib

import discord
from discord.ext import commands
from discord import app_commands

from .utils import get_auditlog_reason, get_dm_embed, hierarchy_check

from Martin import Martin, MartinInteraction
from Utilities.checks import bot_has_permissions, has_permissions


class Moderation(commands.GroupCog, group_name="moderation"):
    """
    Moderation cog.
    """

    def __init__(self, bot: Martin):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="kick", description="Kick a member from this guild.")
    @bot_has_permissions(kick_members=True)
    @has_permissions(kick_members=True)
    @app_commands.describe(
        offender="The offending member that you want to kick.",
        reason="The optional reason for the kick.",
    )
    async def moderation_kick(
        self,
        interaction: MartinInteraction,
        offender: discord.Member,
        reason: str = None,
    ):
        """
        This command respects role hierarchy.

        Except for bot owners LOL.
        """
        if higher := await hierarchy_check(interaction, offender, "kick"):
            return await interaction.response_or_followup(content=higher)

        embed = get_dm_embed(
            interaction.user,
            interaction.guild,
            reason or "No reason was given.",
            "kick",
        )
        with contextlib.suppress(
            discord.errors.Forbidden, discord.errors.HTTPException
        ):
            await offender.send(embed=embed)

        await interaction.guild.kick(
            offender, reason=get_auditlog_reason(interaction.user, reason)
        )
        await interaction.response_or_followup(
            content=f"Member **{offender}** (`{offender.id}`) has been kicked from the guild."
        )

    @app_commands.command(name="ban", description="Ban a member from this guild.")
    @bot_has_permissions(ban_members=True)
    @has_permissions(ban_members=True)
    @app_commands.describe(
        offender="The offending member or user that you want to ban.",
        reason="The optional reason for the ban.",
    )
    async def moderation_ban(
        self,
        interaction: MartinInteraction,
        offender: Union[discord.Member, discord.User],
        reason: str = None,
    ):
        """
        This command respects role hierarchy.

        Except for bot owners LOL.
        """
        if isinstance(offender, discord.Member):
            if higher := await hierarchy_check(interaction, offender, "ban"):
                return await interaction.response_or_followup(content=higher)

        with contextlib.suppress(discord.errors.NotFound):
            await interaction.guild.fetch_ban(offender)
            return await interaction.response_or_followup(
                content=f"User **{offender}** (`{offender.id}`) is already banned."
            )

        embed = get_dm_embed(
            interaction.user,
            interaction.guild,
            reason or "No reason was given.",
            "ban",
        )
        with contextlib.suppress(
            discord.errors.Forbidden, discord.errors.HTTPException
        ):
            await offender.send(embed=embed)

        await interaction.guild.ban(
            offender, reason=get_auditlog_reason(interaction.user, reason)
        )
        await interaction.response_or_followup(
            content=f"{'Member' if isinstance(offender, discord.Member) else 'User'} **{offender}** "
            f"(`{offender.id}`) has been banned from the guild."
        )
