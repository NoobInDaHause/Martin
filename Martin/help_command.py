import inspect
from typing import TYPE_CHECKING, Any, List, Mapping

import discord
from discord.ext import commands

if TYPE_CHECKING:
    from .context import MartinContext


class MartinHelpCommand(commands.HelpCommand):
    context: "MartinContext"

    def __init__(self, **options: Any):
        command_attrs: dict = options.setdefault("command_attrs", {})
        command_attrs.update(
            {
                "cooldown": commands.CooldownMapping.from_cooldown(
                    1, 3.0, commands.BucketType.user
                ),
                "help": "Shows help about the bot, command or category.",
                "hidden": True,
                "aliases": ["h", "hilfe", "hjelp", "cananyonehelpme"],
            }
        )
        super().__init__(**options)

    @staticmethod
    def command_description(command: commands.Command) -> str:
        return inspect.cleandoc(command.help or "No description provided.")

    def format_commands(self, command_list: List[commands.Command]) -> str:
        command_name_width = max((len(command.name) for command in command_list), default=0)
        return "\n".join(
            f"`{command.name:<{command_name_width}}` - "
            f"{self.command_description(command).splitlines()[0]}"
            for command in command_list
        )

    async def send_bot_help(self, mapping: Mapping[Any, Any]) -> None:
        embed = discord.Embed(
            title="Help",
            description="Use `help <command>` for more information.",
            colour=self.context.bot.colour,
        )
        for cog, command_list in mapping.items():
            filtered = await self.filter_commands(command_list, sort=True)
            if filtered:
                cog_name = getattr(cog, "qualified_name", "Other")
                embed.add_field(
                    name=cog_name,
                    value=self.format_commands(filtered),
                    inline=False,
                )
        await self.get_destination().send(embed=embed)

    async def send_cog_help(self, cog: commands.Cog) -> None:
        command_list = await self.filter_commands(cog.get_commands(), sort=True)
        embed = discord.Embed(
            title=f"{cog.qualified_name} commands",
            description="Use `help <command>` for more information.",
            colour=self.context.bot.colour,
        )
        if command_list:
            embed.description = self.format_commands(command_list)
        else:
            embed.description = "No commands available."
        await self.get_destination().send(embed=embed)

    async def send_command_help(self, command: commands.Command) -> None:
        embed = discord.Embed(
            title=f"Help: {command.qualified_name}",
            description=self.command_description(command),
            colour=self.context.bot.colour,
        )
        embed.add_field(name="Usage", value=f"`{self.get_command_signature(command)}`")
        if command.aliases:
            embed.add_field(name="Aliases", value=", ".join(f"`{alias}`" for alias in command.aliases))
        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group: commands.Group) -> None:
        await self.send_command_help(group)
        command_list = await self.filter_commands(group.commands, sort=True)
        if command_list:
            await self.get_destination().send(
                embed=discord.Embed(
                    title=f"{group.qualified_name} subcommands",
                    description=self.format_commands(command_list),
                    colour=self.context.bot.colour,
                )
            )

    async def send_error_message(self, error: str) -> None:
        await self.get_destination().send(f"Help error: {error}")
