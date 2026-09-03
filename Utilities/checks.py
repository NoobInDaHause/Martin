from typing import TYPE_CHECKING

from discord import app_commands

from Utilities.exceptions import UserIsNotOwner

if TYPE_CHECKING:
    from Martin import MartinInteraction


def is_owner():
    async def predicate(interaction: MartinInteraction) -> bool:
        is_owner = await interaction.client.is_owner(interaction.user)
        if not is_owner:
            raise UserIsNotOwner(
                "You must be an owner of this bot to use this command."
            )
        return is_owner

    return app_commands.check(predicate)
