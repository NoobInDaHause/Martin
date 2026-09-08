from typing import TYPE_CHECKING, Union
from datetime import timedelta
import re

from discord import app_commands
from discord.ext import commands

from Utilities.exceptions import BadArgument

if TYPE_CHECKING:
    from Martin import MartinInteraction

TIME_PATTERN = re.compile(
    r"(?P<value>\d+)\s*"
    r"(?P<unit>"
    r"years?|yrs?|y|"
    r"months?|mons?|mo|"
    r"weeks?|w|"
    r"days?|d|"
    r"hours?|hrs?|h|"
    r"minutes?|mins?|m|"
    r"seconds?|secs?|s"
    r")\b",
    re.IGNORECASE,
)


class ParseBoolTransformer(app_commands.Transformer):
    async def transform(
        self, _interaction: "MartinInteraction", value: Union[str, int, bool]
    ) -> bool:
        if isinstance(value, bool):
            return value

        s = str(value).strip().lower()

        truthy = {"yes", "y", "1", "true", "t", "enable", "enabled", "on", "yeah"}
        falsy = {"no", "n", "0", "false", "f", "disable", "disabled", "off", "nah"}

        if s in truthy:
            return True
        if s in falsy:
            return False

        raise BadArgument(f"Cannot convert {value!r} to boolean.")


class UserTransformer(app_commands.Transformer):
    async def transform(self, interaction: "MartinInteraction", value: str):
        try:
            return await commands.UserConverter().convert(
                await interaction.client.get_context(interaction.message), value
            )
        except commands.BadArgument as e:
            raise BadArgument(str(e)) from e


class _TimeDeltaTransformer(app_commands.Transformer):
    async def transform(
        self, interaction: "MartinInteraction", value: str
    ) -> timedelta:
        value = value.strip()

        total = timedelta()
        position = 0
        found = False

        for match in TIME_PATTERN.finditer(value):
            if value[position : match.start()].strip():
                raise BadArgument(
                    f"'{value[position:match.start()].strip()!r}' is not a valid duration."
                )

            number = int(match.group("value"))
            unit = match.group("unit").lower()

            if unit.startswith(("year", "yr")) or unit == "y":
                total += timedelta(days=number * 365)

            elif unit.startswith(("month", "mon")) or unit == "mo":
                total += timedelta(days=number * 30)

            elif unit.startswith("week") or unit == "w":
                total += timedelta(days=number * 7)

            elif unit.startswith("day") or unit == "d":
                total += timedelta(days=number)

            elif unit.startswith(("hour", "hr")) or unit == "h":
                total += timedelta(hours=number)

            elif unit.startswith(("minute", "min")) or unit == "m":
                total += timedelta(minutes=number)

            elif unit.startswith(("second", "sec")) or unit == "s":
                total += timedelta(seconds=number)

            position = match.end()
            found = True

        if not found:
            raise BadArgument(f"'{value!r}' is not a valid duration.")

        if value[position:].strip():
            raise ValueError(f"'{value[position:].strip()!r}' is not a valid duration.")

        return total


# sourcery skip: assign-if-exp
if TYPE_CHECKING:
    TimeDeltaTransformer = timedelta
else:
    TimeDeltaTransformer = _TimeDeltaTransformer
