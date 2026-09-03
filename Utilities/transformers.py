from typing import TYPE_CHECKING, Union
import copy

from discord import app_commands
from discord.ext import commands

if TYPE_CHECKING:
    from Martin import MartinInteraction


class ParseBoolTransformer(app_commands.Transformer):
    async def transform(
        self, interaction: "MartinInteraction", value: Union[str, int, bool]
    ) -> bool:
        if isinstance(value, bool):
            return value

        s = str(value).strip().lower()

        truthy = {"yes", "y", "1", "true", "t", "enable", "enabled", "on"}
        falsy = {"no", "n", "0", "false", "f", "disable", "disabled", "off"}

        if s in truthy:
            return True
        if s in falsy:
            return False

        raise app_commands.TransformerError(f"Cannot convert {value!r} to boolean.")


class UserTransformer(app_commands.Transformer):
    async def transform(self, interaction: "MartinInteraction", value: str):
        try:
            return await commands.UserConverter().convert(
                await interaction.client.get_context(interaction.message), value
            )
        except commands.BadArgument as e:
            raise app_commands.TransformerError(str(e)) from e
