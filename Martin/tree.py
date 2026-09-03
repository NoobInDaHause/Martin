from typing import TYPE_CHECKING
import logging

import discord
from discord import app_commands

from .interaction import MartinInteraction
if TYPE_CHECKING:
    from .bot import Martin


class MartinTree(app_commands.CommandTree):
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

    async def on_error(
        self, interaction: MartinInteraction, error: app_commands.AppCommandError
    ) -> None:
        command = interaction.command
        if command is None:
            self.log.error("Ignoring exception in command tree", exc_info=error)
        elif command._has_any_error_handlers():
            return
        else:
            self.log.error(
                "Ignoring exception in command %r", command.name, exc_info=error
            )
