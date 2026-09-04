from typing import TYPE_CHECKING, List, Union
import contextlib

import discord

from Martin import MartinInteraction

if TYPE_CHECKING:
    from .owner import Owner
    from Cogs.General import General


class CommandModal(discord.ui.Modal):
    command = discord.ui.TextInput(
        label="Command Name:",
        style=discord.TextStyle.short,
        required=True,
        placeholder="Ex: restart",
        max_length=50,
    )
    argument = discord.ui.TextInput(
        label="Argument(s) (Optional):",
        style=discord.TextStyle.long,
        required=False,
        placeholder="Ex: #276a8a",
    )

    async def on_submit(self, interaction: MartinInteraction) -> None:
        await interaction.response.defer()


class OwnerView(discord.ui.View):
    children: List[discord.ui.Button]

    def __init__(self, cog: "Owner", interaction: MartinInteraction, timeout=180):
        super().__init__(timeout=timeout)
        self.message: Union[
            discord.Message, discord.InteractionMessage, discord.WebhookMessage
        ] = None
        self.interaction = interaction
        self.cog = cog

    async def start(self, **kwargs):
        kwargs |= {"view": self}
        self.message = await self.interaction.response_or_followup(**kwargs)

    @discord.ui.button(
        label="Execute a Command", style=discord.ButtonStyle.grey, emoji="📎"
    )
    async def execute_command_button(
        self, interaction: MartinInteraction, button: discord.ui.Button
    ):
        cmdmodal = CommandModal(title="Input a command to execute.", timeout=60.0)
        await interaction.response.send_modal(cmdmodal)
        await cmdmodal.wait()
        if cmdmodal.command.value:
            command = cmdmodal.command.value.lower()
            argument = cmdmodal.argument.value
            req = f"Command '{command}' requires an argument. See the usage from the Owner command panel."
            if command in {"restart", "shutdown"}:
                self.stop()
                await self.on_timeout()
                await self.cog.restart_or_shutdown(
                    interaction, restart=command == "restart"
                )
                return

            if command == "guilds":
                await self.cog._guilds(interaction)
                return

            if command in {"loadcog", "unloadcog", "reloadcog"}:
                if not argument:
                    return await interaction.response_or_followup(
                        content=req, ephemeral=True
                    )
                await self.cog.manage_cogs(
                    interaction, command.removesuffix("cog"), argument.split()
                )
                return

            if command == "coglist":
                await self.cog._cog_list(interaction)
                return

            if command in {"botcolour", "botcolor"}:
                await self.cog._colour(interaction, argument or "#276a8a")
                return

            if command in {"blacklist", "unblacklist"}:
                if not argument:
                    return await self.cog.naughty_list(interaction)
                await self.cog.blacklist_or_unblacklist(
                    command, interaction, argument.split()
                )
                return

            if command == "custominfo":
                if cog := interaction.client.get_cog("General"):
                    cog: "General" = cog
                    if not argument:
                        await cog.db.get_or_delete_custom_info(True)
                    elif await cog.db.get_or_delete_custom_info(False):
                        await cog.db.insert_or_update_custom_info(True, argument)
                    else:
                        await cog.db.insert_or_update_custom_info(False, argument)

                    await interaction.response_or_followup(content="Done.")
                else:
                    await interaction.response_or_followup(content="General cog must be loaded to add/create/remove the custom info.")
                return

            await interaction.response_or_followup(
                content=f"No command called '{command}' found.", ephemeral=True
            )

    @discord.ui.button(emoji="✖️", style=discord.ButtonStyle.danger)
    async def close_button(
        self, interaction: MartinInteraction, button: discord.ui.Button
    ):
        await interaction.response.defer()
        self.stop()
        await self.on_timeout()

    async def interaction_check(self, interaction: MartinInteraction) -> bool:
        if not interaction.user:
            await interaction.response_or_followup(
                content="Hmmm no interaction user found... This interaction is now timed out.",
                ephemeral=True,
            )
            self.stop()
            await self.on_timeout()
            return False

        is_owner = await interaction.client.is_owner(interaction.user)
        if not is_owner:
            await interaction.response_or_followup(
                content="You are not an owner of this bot. 🖕🖕🖕", ephemeral=True
            )
            return is_owner
        return is_owner

    async def on_timeout(self):
        for button in self.children:
            button.disabled = True
        if self.message:
            with contextlib.suppress(discord.errors.NotFound):
                await self.message.edit(view=self)
