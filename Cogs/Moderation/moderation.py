from typing import Dict, Literal, Tuple, Optional, Union
import asyncio
import contextlib
from datetime import datetime, timezone
import logging

import discord
from discord.ext import commands
from discord import app_commands

from .moderation_data_manager import ModerationDataBase
from .objects import TempbanObject
from .utils import get_auditlog_reason, get_dm_embed, hierarchy_check

from Martin import Martin, MartinInteraction
from Utilities.checks import bot_has_permissions, has_permissions
from Utilities.transformers import TimeDeltaTransformer


@app_commands.guild_only()
class Moderation(commands.GroupCog, group_name="moderation"):
    """
    Moderation cog.
    """

    def __init__(self, bot: Martin):
        super().__init__()
        self.bot = bot
        self.db = ModerationDataBase(self.__class__.__name__)
        self.log = logging.getLogger(f"Martin.{self.__class__.__name__}")
        self.initialized = False
        self.tempban_tasks: Dict[Tuple[int, int], asyncio.Task] = {}

    async def init_tempbans(self) -> None:
        await self.bot.wait_until_ready()

        naughty_users = await self.db.get_all_tempbans()

        for g_id, o_id, bui, m_id in naughty_users:
            try:
                guild = await self.bot.get_or_fetch_guild(g_id)
                off = await self.bot.get_or_fetch_user(o_id)
                mod = await self.bot.get_or_fetch_user(m_id)
            except discord.errors.NotFound:
                continue
            else:
                self.tempban_tasks[(guild.id, off.id)] = self.bot.loop.create_task(
                    self.tempban_loop(
                        TempbanObject(
                            offender=off,
                            moderator=mod,
                            guild=guild,
                            timestamp=bui,
                        )
                    )
                )
        self.initialized = True

    async def cog_load(self) -> None:
        self.bot.loop.create_task(self.init_tempbans())

    async def cog_unload(self):
        for task in self.tempban_tasks.values():
            task.cancel()

    async def tempban_loop(self, obj: TempbanObject):
        try:
            while True:
                if not self.initialized:
                    await asyncio.sleep(5)
                    continue

                seconds_left = (obj.until - datetime.now(timezone.utc)).total_seconds()

                if seconds_left <= 0:
                    try:
                        await obj.guild.unban(
                            obj.offender,
                            reason=(
                                f"Tempban issued by {obj.moderator} "
                                f"({obj.moderator.id}) has expired."
                            ),
                        )
                    except discord.errors.Forbidden:
                        self.log.warning(
                            f"Could not unban {obj.offender} from {obj.guild} "
                            "due to missing permissions."
                        )
                        return
                    except discord.errors.NotFound:
                        pass
                    except discord.errors.HTTPException as e:
                        self.log.warning(
                            f"Could not unban {obj.offender} from {obj.guild}: "
                            f"{e}. Retrying in 5 minutes."
                        )
                        await asyncio.sleep(300)
                        continue

                    await self.db.delete_tempban(obj.guild.id, obj.offender.id)
                    return

                await asyncio.sleep(
                    min(seconds_left, 300)
                )  # dont sleep for more than 5 minutes

        except asyncio.CancelledError:
            raise

        finally:
            self.tempban_tasks.pop(
                (obj.guild.id, obj.offender.id),
                None,
            )

    def suicide(self, action: str, offender_id: int, user_id: int) -> Optional[str]:
        if offender_id in (user_id, self.bot.user.id):
            return (
                f"You can not {action} yourself idiot."
                if offender_id == user_id
                else f"I can not {action} myself idiot."
            )

    def _timeout_validation_message(
        self,
        act: Literal["timeout", "untimeout"],
        offender: discord.Member,
        duration: TimeDeltaTransformer,
    ) -> Optional[str]:
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
        if s := self.suicide("kick", offender.id, interaction.user.id):
            return await interaction.response_or_followup(content=s)

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
        if s := self.suicide("ban", offender.id, interaction.user.id):
            return await interaction.response_or_followup(content=s)

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
        if s := self.suicide("unban", offender.id, interaction.user.id):
            return await interaction.response_or_followup(content=s)

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

        if task := self.tempban_tasks.get((interaction.guild.id, offender.id)):
            task.cancel()

        await self.db.delete_tempban(interaction.guild.id, offender.id)

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
        if s := self.suicide(act, offender.id, interaction.user.id):
            return await interaction.response_or_followup(content=s)

        if higher := await hierarchy_check(interaction, offender, act):
            return await interaction.response_or_followup(content=higher)

        if message := self._timeout_validation_message(act, offender, duration):
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
        if s := self.suicide("tempban", offender.id, interaction.user.id):
            return await interaction.response_or_followup(content=s)

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
        timestamp = int(until.timestamp())
        await self.db.insert_tempban(
            interaction.guild.id,
            offender.id,
            timestamp,
            interaction.user.id,
        )
        self.tempban_tasks[(interaction.guild.id, offender.id)] = (
            self.bot.loop.create_task(
                self.tempban_loop(
                    TempbanObject(
                        offender=offender,
                        moderator=interaction.user,
                        guild=interaction.guild,
                        timestamp=timestamp,
                    )
                )
            )
        )
        await interaction.response_or_followup(
            content=f"{u} **{offender}** (`{offender.id}`) has been temporarily banned from the guild till "
            f"<t:{int(until.timestamp())}:F> (<t:{int(until.timestamp())}:R>)"
        )
