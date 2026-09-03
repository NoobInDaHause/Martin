from typing import TYPE_CHECKING, Union

from discord import app_commands

if TYPE_CHECKING:
    from Martin import MartinInteraction


class ParseBoolTransformer(app_commands.Transformer):
    async def transform(
        self, interaction: "MartinInteraction", value: Union[str, int, bool]
    ) -> bool:
        if isinstance(value, bool):
            return value

        # Convert to lowercase string and strip whitespace
        s = str(value).strip().lower()

        truthy = {"yes", "y", "1", "true", "t", "enable", "enabled", "on"}
        falsy = {"no", "n", "0", "false", "f", "disable", "disabled", "off"}

        if s in truthy:
            return True
        if s in falsy:
            return False

        raise ValueError(f"Cannot convert {value!r} to boolean.")
