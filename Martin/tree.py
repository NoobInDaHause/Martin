from typing import TYPE_CHECKING
from datetime import datetime, timedelta, timezone
import logging

import discord
from discord import app_commands

from Utilities.exceptions import BadArgument, UserIsBlacklisted, UserIsNotOwner

from .interaction import MartinInteraction

if TYPE_CHECKING:
    from .bot import Martin


class MartinTree(app_commands.CommandTree["Martin"]):
    def __init__(
        self,
        client: "Martin",
        *,
        fallback_to_global: bool = True,
        allowed_contexts: app_commands.AppCommandContext = discord.utils.MISSING,
        allowed_installs: app_commands.AppInstallationType = discord.utils.MISSING,
    ):
        super().__init__(
            client,
            fallback_to_global=fallback_to_global,
            allowed_contexts=allowed_contexts,
            allowed_installs=allowed_installs,
        )
        self.log = logging.getLogger("MartinTree")

    async def interaction_check(self, interaction: MartinInteraction):
        if self.client.is_blacklisted(
            interaction.user
        ) and not await self.client.is_owner(interaction.user):
            raise UserIsBlacklisted(
                "LOL you are blacklisted from using this bot. Get wrecked idiot."
            )
        return await super().interaction_check(interaction)

    async def on_error(
        self, interaction: MartinInteraction, error: app_commands.AppCommandError
    ) -> None:
        command = interaction.command
        if command is None:
            self.log.error("Ignoring exception in command tree", exc_info=error)
            return

        self.client.dispatch("app_command_error", interaction, error)
        if command._has_any_error_handlers():
            return

        owner_message = (
            "Check your console or logs for details."
            if await interaction.client.is_owner(interaction.user)
            else "Please report this to the bot owner."
        )
        error_msg = f"Error in command `'{command}'`. {owner_message}"

        if isinstance(error, app_commands.CommandInvokeError):
            self.log.error(
                "SlashCommand %s failed.",
                interaction.command,
                exc_info=(type(error), error, error.__traceback__),
            )
            await interaction.response_or_followup(content=error_msg, ephemeral=True)
            return

        if isinstance(error, (UserIsNotOwner, UserIsBlacklisted)):
            await interaction.response_or_followup(content=str(error), ephemeral=True)
            self.log.info(
                "User %s (%s) %s command in channel #%s (%s). Command: '/%s'",
                interaction.user,
                interaction.user.id,
                (
                    "tried to run an owner only"
                    if isinstance(error, UserIsNotOwner)
                    else "is blacklisted and tried to run"
                ),
                (
                    "DM Channel"
                    if isinstance(interaction.channel, discord.DMChannel)
                    else interaction.channel
                ),
                interaction.channel.id,
                command.qualified_name,
            )
            return

        if isinstance(
            error,
            (
                app_commands.NoPrivateMessage,
                app_commands.MissingRole,
                app_commands.MissingAnyRole,
                app_commands.MissingPermissions,
                app_commands.BotMissingPermissions,
                BadArgument,
            ),
        ):
            await interaction.response_or_followup(content=str(error))
            return

        if isinstance(error, app_commands.CommandOnCooldown):
            time_left = datetime.now(timezone.utc) + timedelta(
                seconds=error.retry_after
            )
            await interaction.response_or_followup(
                content=f"This command is on cooldown. Try again in <t:{int(time_left.timestamp())}:R>.",
                ephemeral=True,
            )
            return

        if isinstance(
            error, app_commands.CheckFailure
        ):  # will put this second to last since some of the errors above inherrit this
            await interaction.response_or_followup(content=str(error))
            return

        self.log.error(
            "Unhandled slash command error in %s",
            command.qualified_name,
            exc_info=(type(error), error, error.__traceback__),
        )
        await interaction.response_or_followup(content=error_msg, ephemeral=True)
