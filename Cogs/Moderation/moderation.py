import asyncio
import contextlib
import logging
from datetime import datetime, timezone
from typing import Dict, Literal, Optional, Tuple, Union

import discord
from discord import app_commands
from discord.ext import commands

from Martin import Martin, MartinInteraction
from Utilities.checks import bot_has_permissions, has_permissions
from Utilities.formatting import pagify
from Utilities.transformers import TimeDeltaTransformer
from Utilities.views import PaginatorView

from .moderation_data_manager import ModerationDataBase
from .objects import TempbanObject
from .utils import get_auditlog_reason, get_dm_embed, get_modlog_embed, hierarchy_check


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
        self.initialized = asyncio.Event()
        self.tempban_tasks: Dict[Tuple[int, int], asyncio.Task] = {}
        self.tempban_targets = set()
        self.unban_targets = set()
        self.kick_targets = set()
        self.timeout_targets = set()

    @commands.Cog.listener("on_member_ban")
    async def log_bans(self, guild: discord.Guild, user: discord.User):
        if (guild.id, user.id) in self.tempban_targets:
            return

        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.ban):
            if entry.target.id == user.id:
                moderator = entry.user
                reason = entry.reason

                case_id = await self.db.insert_modlog(
                    guild.id,
                    "ban",
                    user.id,
                    moderator.id,
                    reason,
                )

                with contextlib.suppress(
                    discord.errors.Forbidden, discord.errors.NotFound
                ):
                    await self.send_to_modlog(
                        guild.id,
                        "ban",
                        case_id,
                        user,
                        moderator,
                        reason,
                    )
                break

    @commands.Cog.listener("on_member_unban")
    async def log_unban(self, guild: discord.Guild, user: discord.User):
        if (guild.id, user.id) in self.unban_targets:
            return

        async for entry in guild.audit_logs(
            limit=5, action=discord.AuditLogAction.unban
        ):
            if entry.target.id == user.id:
                if task := self.tempban_tasks.get((guild.id, user.id)):
                    task.cancel()

                moderator = entry.user
                reason = entry.reason

                case_id = await self.db.insert_modlog(
                    guild.id,
                    "unban",
                    user.id,
                    moderator.id,
                    reason,
                )

                with contextlib.suppress(
                    discord.errors.Forbidden, discord.errors.NotFound
                ):
                    await self.send_to_modlog(
                        guild.id,
                        "unban",
                        case_id,
                        user,
                        moderator,
                        reason,
                    )
                break

    @commands.Cog.listener("on_member_update")
    async def log_timeouts(self, before: discord.Member, after: discord.Member):
        if (before.guild.id, before.id) in self.timeout_targets:
            return

        was_timed_out = before.is_timed_out()
        is_timed_out = after.is_timed_out()
        guild = before.guild

        if not was_timed_out and is_timed_out:
            action = "timeout"
        elif was_timed_out and not is_timed_out:
            action = "untimeout"
        else:
            return

        async for entry in after.guild.audit_logs(
            limit=10, action=discord.AuditLogAction.member_update
        ):
            if entry.target.id == after.id:
                moderator = entry.user
                reason = entry.reason

                case_id = await self.db.insert_modlog(
                    guild.id,
                    action,
                    after.id,
                    moderator.id,
                    reason,
                )

                with contextlib.suppress(
                    discord.errors.Forbidden, discord.errors.NotFound
                ):
                    await self.send_to_modlog(
                        guild.id,
                        action,
                        case_id,
                        after,
                        moderator,
                        reason,
                    )
                break

    @commands.Cog.listener("on_member_remove")
    async def log_kicks(self, member: discord.Member):
        if (member.guild.id, member.id) in self.kick_targets:
            return

        await asyncio.sleep(1)

        async for entry in member.guild.audit_logs(
            limit=5, action=discord.AuditLogAction.kick
        ):
            if entry.target.id == member.id:
                moderator = entry.user
                reason = entry.reason

                case_id = await self.db.insert_modlog(
                    member.guild.id,
                    "kick",
                    member.id,
                    moderator.id,
                    reason,
                )

                with contextlib.suppress(
                    discord.errors.Forbidden, discord.errors.NotFound
                ):
                    await self.send_to_modlog(
                        member.guild.id,
                        "kick",
                        case_id,
                        member,
                        moderator,
                        reason,
                    )
                break

    async def send_to_modlog(
        self,
        guild_id: int,
        action: str,
        case_id: int,
        offender: discord.User,
        moderator: discord.Member,
        reason: str = None,
        until_timestamp: int = None,
    ) -> None:
        if exists := await self.db.modlog_channel("get", guild_id):
            if channel := await self.bot.get_or_fetch_channel(guild_id, exists[0][0]):
                await channel.send(
                    embed=get_modlog_embed(
                        action, case_id, offender, moderator, reason, until_timestamp
                    )
                )

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
        self.initialized.set()

    async def cog_load(self) -> None:
        await self.db.initialize()
        self.bot.loop.create_task(self.init_tempbans())

    async def cog_unload(self):
        for task in self.tempban_tasks.values():
            task.cancel()
        self.initialized.clear()

    async def tempban_loop(self, obj: TempbanObject):
        await self.initialized.wait()

        try:
            while True:
                seconds_left = (obj.until - datetime.now(timezone.utc)).total_seconds()

                if seconds_left <= 0:
                    try:
                        self.unban_targets.add((obj.guild.id, obj.offender.id))
                        await obj.guild.unban(
                            obj.offender,
                            reason=(
                                f"Tempban issued by {obj.moderator} "
                                f"({obj.moderator.id}) has expired."
                            ),
                        )
                        case_id = await self.db.insert_modlog(
                            obj.guild.id,
                            "unban",
                            obj.offender.id,
                            obj.moderator.id,
                            "Temporay ban has expired.",
                        )

                        with contextlib.suppress(
                            discord.errors.Forbidden, discord.errors.NotFound
                        ):
                            await self.send_to_modlog(
                                obj.guild.id,
                                "unban",
                                case_id,
                                obj.offender,
                                obj.moderator,
                                "Temporary ban has expired.",
                            )
                    except discord.errors.Forbidden:
                        self.log.warning(
                            f"Could not unban {obj.offender} from {obj.guild} "
                            "due to missing permissions."
                        )
                        self.unban_targets.discard((obj.guild.id, obj.offender.id))
                        return
                    except discord.errors.NotFound:
                        pass
                    except discord.errors.HTTPException as e:
                        self.log.warning(
                            f"Could not unban {obj.offender} from {obj.guild}: "
                            f"{e}. Retrying in 5 minutes."
                        )
                        self.unban_targets.discard((obj.guild.id, obj.offender.id))
                        await asyncio.sleep(300)
                        continue

                    self.unban_targets.discard((obj.guild.id, obj.offender.id))

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

        self.timeout_targets.add((interaction.guild.id, offender.id))
        await offender.timeout(
            until, reason=get_auditlog_reason(interaction.user, reason)
        )
        case_id = await self.db.insert_modlog(
            interaction.guild.id,
            act,
            offender.id,
            interaction.user.id,
            reason,
        )

        with contextlib.suppress(discord.errors.Forbidden, discord.errors.NotFound):
            await self.send_to_modlog(
                interaction.guild.id,
                act,
                case_id,
                offender,
                interaction.user,
                reason,
            )
        self.timeout_targets.discard((interaction.guild.id, offender.id))

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

        self.kick_targets.add((interaction.guild.id, offender.id))
        await interaction.guild.kick(
            offender, reason=get_auditlog_reason(interaction.user, reason)
        )
        case_id = await self.db.insert_modlog(
            interaction.guild.id,
            "kick",
            offender.id,
            interaction.user.id,
            reason,
        )

        with contextlib.suppress(discord.errors.Forbidden, discord.errors.NotFound):
            await self.send_to_modlog(
                interaction.guild.id,
                "kick",
                case_id,
                offender,
                interaction.user,
                reason,
            )
        self.kick_targets.discard((interaction.guild.id, offender.id))

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

        self.tempban_targets.add((interaction.guild.id, offender.id))
        await interaction.guild.ban(
            offender, reason=get_auditlog_reason(interaction.user, reason)
        )
        case_id = await self.db.insert_modlog(
            interaction.guild.id,
            "ban",
            offender.id,
            interaction.user.id,
            reason,
        )

        with contextlib.suppress(discord.errors.Forbidden, discord.errors.NotFound):
            await self.send_to_modlog(
                interaction.guild.id,
                "ban",
                case_id,
                offender,
                interaction.user,
                reason,
            )
        self.tempban_targets.discard((interaction.guild.id, offender.id))

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

        self.unban_targets.add((interaction.guild.id, offender.id))
        await interaction.guild.unban(
            offender, reason=get_auditlog_reason(interaction.user, reason)
        )

        case_id = await self.db.insert_modlog(
            interaction.guild.id,
            "unban",
            offender.id,
            interaction.id,
            reason,
        )

        with contextlib.suppress(discord.errors.Forbidden, discord.errors.NotFound):
            await self.send_to_modlog(
                interaction.guild.id,
                "unban",
                case_id,
                offender,
                interaction.user,
                reason,
            )
        self.unban_targets.discard((interaction.guild.id, offender.id))

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

        self.tempban_targets.add((interaction.guild.id, offender.id))
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

        case_id = await self.db.insert_modlog(
            interaction.guild.id,
            "tempban",
            offender.id,
            interaction.user.id,
            reason,
            timestamp,
        )
        self.tempban_targets.discard((interaction.guild.id, offender.id))

        try:
            await self.send_to_modlog(
                interaction.guild.id,
                "tempban",
                case_id,
                offender,
                interaction.user,
                reason,
                timestamp,
            )
        except (discord.errors.Forbidden, discord.errors.NotFound):
            await interaction.channel.send(
                content="Could not send log to modlog channel, it is either deleted or missing permission."
            )

        await interaction.response_or_followup(
            content=f"{u} **{offender}** (`{offender.id}`) has been temporarily banned from the guild till "
            f"<t:{int(until.timestamp())}:F> (<t:{int(until.timestamp())}:R>)"
        )

    @app_commands.command(name="warning", description="Warn a member.")
    @has_permissions(manage_messages=True)
    @app_commands.describe(
        action="The action that you want to perform.",
        offender="The offending member.",
        reason="The optional reason.",
    )
    async def moderation_warning(
        self,
        interaction: MartinInteraction,
        action: Literal["add", "remove", "list"],
        offender: discord.Member,
        reason: str = None,
    ) -> None:
        """
        This command respects role hierarchy.

        Except for bot owners LOL.
        """
        await interaction.response.defer(thinking=True)
        act = "warn" if action == "add" else "unwarn"
        if (
            s := self.suicide(act, offender.id, interaction.user.id)
            and action != "list"
        ):
            return await interaction.response_or_followup(content=s)

        if (
            higher := await hierarchy_check(interaction, offender, act)
            and action != "list"
        ):
            return await interaction.response_or_followup(content=higher)

        match action:
            case "add":
                await self.db.insert_warning(
                    interaction.guild.id, offender.id, interaction.user.id, reason
                )
            case "remove":
                exists = await self.db.get_all_warnings_from_offender(
                    interaction.guild.id, offender.id
                )
                if not exists:
                    return await interaction.response_or_followup(
                        content="This member has no warnings."
                    )
                await self.db.delete_warning(
                    interaction.guild.id, max(i[1] for i in exists)
                )
            case "list":
                exists = await self.db.get_all_warnings_from_offender(
                    interaction.guild.id, offender.id
                )
                if not exists:
                    return await interaction.response_or_followup(
                        content="This member has no warnings."
                    )
                pagified = pagify(
                    "".join(
                        f"#{w_id}\nModerator: <@{m_id}>\nReason: {r}\n\n"
                        for _, w_id, _, m_id, r in exists
                    ),
                    "\n\n",
                )
                embeds = []
                for index, page in enumerate(pagified, 1):
                    embed = discord.Embed(
                        title=f"Warnings for **{offender}** (`{offender.id}`)",
                        description=page,
                        colour=offender.colour,
                    )
                    embed.set_footer(text=f"Page ({index}/{len(pagified)})")
                    embeds.append(embed)
                return await PaginatorView(interaction, embeds).start()

        with contextlib.suppress(
            discord.errors.Forbidden, discord.errors.HTTPException
        ):
            await offender.send(
                embed=get_dm_embed(
                    interaction.user,
                    interaction.guild,
                    reason or "No reason was given.",
                    act,
                )
            )

        case_id = await self.db.insert_modlog(
            interaction.guild.id, act, offender.id, interaction.user.id, reason
        )

        try:
            await self.send_to_modlog(
                interaction.guild.id, act, case_id, offender, interaction.user, reason
            )
        except (discord.errors.Forbidden, discord.errors.NotFound):
            await interaction.channel.send(
                content="Could not send log to modlog channel, it is either deleted or missing permission."
            )

        await interaction.response_or_followup(
            content=f"Member **{offender}** (`{offender.id}`) has been {act}ed."
        )

    @app_commands.command(
        name="modlog", description="Set the logging channel for mod actions."
    )
    @has_permissions(manage_channels=True)
    @app_commands.describe(
        action="Action to perform.", channel="The channel that you want to set."
    )
    async def moderation_modlog(
        self,
        interaction: MartinInteraction,
        action: Literal["set", "remove", "view"],
        channel: discord.TextChannel = None,
    ) -> None:
        """
        This command respects role hierarchy.

        Except for bot owners LOL.
        """
        channel_id = channel.id if channel else None
        guild_id = interaction.guild.id
        exist = await self.db.modlog_channel("get", guild_id, channel_id)

        to_send = ""
        match action:
            case "set":
                if channel is None:
                    to_send += "Channel is required to set modlog."
                elif not channel.permissions_for(interaction.guild.me).send_messages:
                    to_send += f"I cannot send messages to {channel.mention}. Please check my permissions."
                else:
                    await self.db.modlog_channel(
                        "update" if exist else "insert",
                        guild_id,
                        channel_id,
                    )
                    to_send += f"{channel.mention} has been set as the modlog channel."

            case "remove":
                if not exist:
                    to_send += "There is no modlog channel currently set to remove."
                else:
                    await self.db.modlog_channel("delete", guild_id)
                    to_send += "The modlog channel has been cleared."

            case "view":
                to_send += (
                    f"<#{exist[0][0]}> is the set modlog channel."
                    if exist
                    else "No modlog channel has been set."
                )

        await interaction.response_or_followup(content=to_send)
