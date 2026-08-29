import contextlib
from typing import TYPE_CHECKING, List, Optional, Union

import discord

from Martin.interaction import response_or_followup

if TYPE_CHECKING:
    from Martin import MartinContext, MartinInteraction


class ConfirmationView(discord.ui.View):
    children: List[discord.ui.Button]

    def __init__(
        self,
        obj: Union["MartinContext", "MartinInteraction"],
        confirmed_content: str = "Action confirmed.",
        confirmed_embed: Optional[discord.Embed] = None,
        timeout: float = 30.0,
    ):
        super().__init__(timeout=timeout)
        self.message: Optional[Union[discord.Message, discord.WebhookMessage]] = None
        self.obj = obj
        self.confirmed_content = confirmed_content
        self.confirmed_embed = confirmed_embed
        self.value: Optional[bool] = None

    async def start(self, *args, **kwargs) -> None:
        self.message = (
            await response_or_followup(self.obj, *args, **kwargs)
            if isinstance(self.obj, discord.Interaction)
            else await self.obj.send(*args, **kwargs)
        )

    @discord.ui.button(emoji="✔️", style=discord.ButtonStyle.success)
    async def confirm_button(
        self, interaction: "MartinInteraction", button: discord.ui.Button
    ) -> None:
        self.value = True
        self.reject_button.style = discord.ButtonStyle.grey
        self.reject_button.disabled = True
        button.disabled = True
        await interaction.response.edit_message(
            content=self.confirmed_content, embed=self.confirmed_embed, view=self
        )
        self.stop()

    @discord.ui.button(emoji="✖️", style=discord.ButtonStyle.danger)
    async def reject_button(
        self, interaction: "MartinInteraction", button: discord.ui.Button
    ) -> None:
        self.value = False
        self.confirm_button.style = discord.ButtonStyle.grey
        self.confirm_button.disabled = True
        button.disabled = True
        await interaction.response.edit_message(
            content="Alright not doing that then.", embed=None, view=self
        )
        self.stop()

    async def interaction_check(self, interaction: "MartinInteraction") -> bool:
        if not interaction.user:
            await interaction.response.send_message(
                content="Hmmm no interaction user found... This interaction is now timed out.",
                ephemeral=True,
            )
            await self.on_timeout()
            return False
        if await interaction.client.is_owner(interaction.user):
            return True
        author = (
            self.obj.user
            if isinstance(self.obj, discord.Interaction)
            else self.obj.author
        )
        if interaction.user.id != author.id:
            await interaction.response.send_message(
                content="You are not authorized to interact with this interaction.",
                ephemeral=True,
            )
            return False
        return True

    async def on_timeout(self) -> None:
        self.stop()
        for button in self.children:
            button.disabled = True
        if self.message:
            with contextlib.suppress(discord.errors.NotFound):
                await self.message.edit(view=self)
