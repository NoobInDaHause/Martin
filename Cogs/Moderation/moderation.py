from typing import Dict, Literal, Optional, Union
import contextlib
from copy import copy
from datetime import datetime, timezone
import logging

import discord
from discord.ext import commands, tasks
from discord import app_commands

from .moderation_data_manager import ModerationDataBase
from .utils import get_auditlog_reason, get_dm_embed, hierarchy_check

from Martin import Martin, MartinInteraction
from Utilities.checks import bot_has_permissions, has_permissions
from Utilities.transformers import TimeDeltaTransformer


class Moderation(commands.GroupCog, group_name="moderation"):
    """
    Moderation cog.
    """

    def __init__(self, bot: Martin):
        super().__init__()
        self.bot = bot
        self.db = ModerationDataBase(self.__class__.__name__)
        self.tempban_cache: Dict[int, Dict[int, datetime]] = {}
        self.log = logging.getLogger(f"Martin.{self.__class__.__name__}")
        self.initialized = False

    async def init_tempbans(self) -> None:
        naughty_users = await self.db.get_all_tempbans()
        for g_id, o_id, bui in naughty_users:
            cache = self.tempban_cache.setdefault(g_id, {})
            cache |= {o_id: datetime.fromtimestamp(bui, tz=timezone.utc)}
        self.initialized = True

    async def cog_load(self) -> None:
        await self.db.initialize()
        await self.init_tempbans()
        self.tempban_loop.start()
        self.log.info("Tempban task loop started.")

    async def cog_unload(self):
        self.tempban_cache = {}
        self.tempban_loop.stop()
        self.log.info("Tempban task loop stopped.")

    @tasks.loop(seconds=5.0)
    async def tempban_loop(self):
        if not self.initialized:
            return

        copied = copy(self.tempban_cache)
        for g_id, tempbans in copied.items():
            if guild := self.bot.get_guild(g_id):
                for o_id, bui in tempbans.items():
                    if bui < datetime.now(timezone.utc):
                        try:
                            offender = await self.bot.get_or_fetch_user(o_id)
                            await guild.unban(offender, reason="Tempban expired.")
                        except discord.errors.NotFound:
                            self.tempban_cache[g_id].pop(o_id, None)
                        except discord.errors.Forbidden:
                            continue
                        await self.db.get_or_delete_tempban(True, g_id, o_id)

    @tempban_loop.before_loop
    async def before_tempban_loop(self):
        await self.bot.wait_until_ready()

    def _timeout_validation_message(
        self,
        interaction: MartinInteraction,
        act: Literal["timeout", "untimeout"],
        offender: discord.Member,
        duration: TimeDeltaTransformer,
    ) -> Optional[str]:
        if offender.id in (interaction.user.id, self.bot.user.id):
            return (
                f"You can not {act} yourself idiot."
                if offender.id == interaction.user.id
                else f"I can not {act} myself idiot."
            )

        if act == "untimeout":
            if not offender.is_timed_out():
                return f"Member {offender} (`{offender.id}`) is not timed out."
            return

        if offender.is_timed_out():
            return f"Member {offender} (`{offender.id}`) is already timed out."
        if duration is None:
            return "You must provide a duration if you want to timeout a member."

        seconds = int(duration.total_seconds())
        if seconds < 60:
            return "Duration must not be less than 1 minute."
        if seconds > 604800 * 4:
            return "Duration must not be longer than 28 days."

    async def _apply_timeout(
        self,
        interaction: MartinInteraction,
        act: Literal["timeout", "untimeout"],
        offender: discord.Member,
        duration: TimeDeltaTransformer,
        reason: str = None,
    ) -> None:
        until = datetime.now(timezone.utc) + duration if act == "timeout" else None

        with contextlib.suppress(
            discord.errors.Forbidden, discord.errors.HTTPException
        ):
            await offender.send(
                embed=get_dm_embed(
                    interaction.user,
                    interaction.guild,
                    reason or "No reason was given.",
                    act,
                    until,
                )
            )

        await offender.timeout(
            until, reason=get_auditlog_reason(interaction.user, reason)
        )

        if act == "timeout":
            content = (
                f"Member {offender} (`{offender.id}`) has been timed out until "
                f"<t:{int(until.timestamp())}:F> "
                f"(<t:{int(until.timestamp())}:R>)"
            )
        else:
            content = f"Member {offender} (`{offender.id}`) has been untimed out."

        await interaction.response_or_followup(content=content)

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
    ) -> None:
        """
        This command respects role hierarchy.

        Except for bot owners LOL.
        """
        if higher := await hierarchy_check(interaction, offender, "kick"):
            return await interaction.response_or_followup(content=higher)

        with contextlib.suppress(
            discord.errors.Forbidden, discord.errors.HTTPException
        ):
            await offender.send(
                embed=get_dm_embed(
                    interaction.user,
                    interaction.guild,
                    reason or "No reason was given.",
                    "kick",
                )
            )

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
                content=f"User **{offender}** (`{offender.id}`) is already banned from this guild."
            )

        with contextlib.suppress(
            discord.errors.Forbidden, discord.errors.HTTPException
        ):
            await offender.send(
                embed=get_dm_embed(
                    interaction.user,
                    interaction.guild,
                    reason or "No reason was given.",
                    "ban",
                )
            )

        await interaction.guild.ban(
            offender, reason=get_auditlog_reason(interaction.user, reason)
        )
        await interaction.response_or_followup(
            content=f"{'Member' if isinstance(offender, discord.Member) else 'User'} **{offender}** "
            f"(`{offender.id}`) has been banned from the guild."
        )

    @app_commands.command(name="unban", description="Unban a user from this guild.")
    @bot_has_permissions(ban_members=True)
    @has_permissions(ban_members=True)
    @app_commands.describe(
        offender="The user that you want to unban.",
        reason="The optional reason for the unban.",
    )
    @app_commands.rename(offender="offender_id")
    async def moderation_unban(
        self,
        interaction: MartinInteraction,
        offender: discord.User,
        reason: str = None,
    ):
        """
        This command respects role hierarchy.

        Except for bot owners LOL.
        """
        try:
            await interaction.guild.fetch_ban(offender)
        except discord.errors.NotFound:
            return await interaction.response_or_followup(
                content=f"User **{offender}** (`{offender.id}`) is not banned from this guild."
            )

        with contextlib.suppress(
            discord.errors.Forbidden, discord.errors.HTTPException
        ):
            await offender.send(
                embed=get_dm_embed(
                    interaction.user,
                    interaction.guild,
                    reason or "No reason was given.",
                    "unban",
                )
            )

        await interaction.guild.unban(
            offender, reason=get_auditlog_reason(interaction.user, reason)
        )
        await self.db.get_or_delete_tempban(True, interaction.guild.id, offender.id)
        if g_id := self.tempban_cache.get(interaction.guild.id):
            g_id.pop(offender.id, None)
        await interaction.response_or_followup(
            content=f"User **{offender}** (`{offender.id}`) has been unbanned from the guild."
        )

    @app_commands.command(
        name="timeout",
        description="Timeout or untimeout a naughty member from this guild.",
    )
    @bot_has_permissions(moderate_members=True)
    @has_permissions(moderate_members=True)
    @app_commands.describe(
        act="Timeout or untimeout.",
        offender="The offending member that you want to timeout/untimeout.",
        duration="The duration of the timeout. Example: `1h25m30s` -> 1 hour, 25 minutes and 30 seconds.",
        reason="The optional reason for the timeout/untimeout.",
    )
    @app_commands.rename(act="action")
    async def moderation_timeout(
        self,
        interaction: MartinInteraction,
        act: Literal["timeout", "untimeout"],
        offender: discord.Member,
        duration: TimeDeltaTransformer = None,
        reason: str = None,
    ) -> None:
        """
        This command respects role hierarchy.

        Except for bot owners LOL.
        """
        if higher := await hierarchy_check(interaction, offender, act):
            return await interaction.response_or_followup(content=higher)

        if message := self._timeout_validation_message(
            interaction, act, offender, duration
        ):
            return await interaction.response_or_followup(content=message)

        await self._apply_timeout(interaction, act, offender, duration, reason)

    @app_commands.command(name="tempban", description="Temporarily bans an offender.")
    @bot_has_permissions(ban_members=True)
    @has_permissions(ban_members=True)
    @app_commands.describe(
        offender="The offending member or user.",
        duration="The duration of the tempban. (minimum 10s)",
        reason="The optional reason for the tempban.",
    )
    async def moderation_tempban(
        self,
        interaction: MartinInteraction,
        offender: Union[discord.Member, discord.User],
        duration: TimeDeltaTransformer,
        reason: str = None,
    ) -> None:
        """
        This command respects role hierarchy.

        Except for bot owners LOL.
        """
        if isinstance(offender, discord.Member):
            if higher := await hierarchy_check(interaction, offender, "ban"):
                return await interaction.response_or_followup(content=higher)

        u = "User" if isinstance(offender, discord.User) else "Member"

        with contextlib.suppress(discord.errors.NotFound):
            await interaction.guild.fetch_ban(offender)
            return await interaction.response_or_followup(
                content=f"{u} **{offender}** (`{offender.id}`) is already banned from this guild."
            )

        if int(duration.total_seconds()) < 10:
            return await interaction.response_or_followup(
                content="Duration must not be less than 10 seconds."
            )

        until = datetime.now(timezone.utc) + duration

        with contextlib.suppress(
            discord.errors.Forbidden, discord.errors.HTTPException
        ):
            await offender.send(
                embed=get_dm_embed(
                    interaction.user,
                    interaction.guild,
                    reason or "No reason was given.",
                    "tempban",
                    until,
                )
            )

        await interaction.guild.ban(
            offender, reason=get_auditlog_reason(interaction.user, reason)
        )
        await self.db.insert_tempban(
            interaction.guild.id, offender.id, int(until.timestamp())
        )
        cache = self.tempban_cache.setdefault(interaction.guild.id, {})
        cache |= {offender.id: until}
        await interaction.response_or_followup(
            content=f"{u} **{offender}** (`{offender.id}`) has been temporarily banned from the guild till "
            f"<t:{int(until.timestamp())}:F> (<t:{int(until.timestamp())}:R>)"
        )
