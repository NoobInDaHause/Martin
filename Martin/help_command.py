import inspect
from typing import TYPE_CHECKING, Any, List, Mapping, Optional, Union

import discord
from discord.ext import commands

from Utilities.formatting import format_list, format_time, pagify
from Utilities.views import PaginatorView

if TYPE_CHECKING:
    from .context import MartinContext


class MartinHelpCommand(commands.HelpCommand):
    COMMAND_NAME_WIDTH = 15
    context: "MartinContext"

    @staticmethod
    def command_description(command: commands.Command) -> str:
        return inspect.cleandoc(command.help or "No description provided.")

    async def command_callback(self, ctx: MartinContext, /, *, command: Optional[str] = None) -> None:
        check = commands.bot_has_permissions(embed_links=True)
        await check.predicate(ctx)
        return await super().command_callback(ctx, command=command)

    @staticmethod
    def get_bot_permissions(command: commands.Command) -> Optional[str]:
        if command.qualified_name == "help":
            return "`Embed Links`"

        source_lines = inspect.getsource(command.callback).split("\n")
        for line in source_lines:
            if "@" in line and "bot_has_permissions" in line:
                permissions = line.split("(")[1].replace(")", "").split(",")
                final_permissions = [
                    perm.strip().split("=")[0]
                    for perm in permissions
                    if perm.strip().split("=")[1] == "True"
                ]
                list_str = [
                    f"`{perm.replace('_', ' ').strip().title()}`"
                    for perm in final_permissions
                ]
                return format_list(list(sorted(list_str)))

    @staticmethod
    def get_user_permissions(
        command: Union[commands.Command, commands.Group],
    ) -> Optional[str]:
        source_lines = inspect.getsource(command.callback).split("\n")
        list_str = []
        for check in command.checks:
            if "is_owner" in str(check):
                list_str.append("`Bot Owner`")
                break
        for line in source_lines:
            if "@" in line and "has_permissions" in line and "bot" not in line:
                permissions = line.split("(")[1].replace(")", "").split(",")
                final_permissions = [
                    perm.strip().split("=")[0]
                    for perm in permissions
                    if perm.strip().split("=")[1] == "True"
                ]
                list_str.extend(
                    [f"`{p.replace('_', ' ').title()}`" for p in final_permissions]
                )
                break
        return format_list(list(sorted(list_str)), "or")

    @staticmethod
    def get_command_cooldown_and_max_concurrency(
        command: Union[commands.Command, commands.Group],
    ) -> Optional[str]:
        cooldowns = []
        if cd := command._buckets._cooldown:
            txt = (
                f"`Can be run:` **{cd.rate}** time{'s' if cd.rate > 1 else ''} every "
                f"**{format_time(seconds=cd.per)}**"
            )
            if buckettype := getattr(cd, "type", None):
                if bucketname := getattr(buckettype, "name", None):
                    txt += f" per **{bucketname}**"
            cooldowns.append(txt)

        if mc := command._max_concurrency:
            cooldowns.append(
                f"`Maximum concurrent uses:` **{mc.number:,}** "
                f"time{'s' if mc.number > 1 else ''} per **{mc.per.name.capitalize()}**"
            )

        return "\n".join(cooldowns)

    def split_subcommand_embed(
        self, embed: discord.Embed, command_str: str
    ) -> List[discord.Embed]:
        pagified_str: List[str] = pagify(command_str, delims=["\n"], page_length=512)

        embeds: List[discord.Embed] = []

        for index, page in enumerate(pagified_str, 1):
            new_embed = discord.Embed.from_dict(embed.to_dict())
            new_embed.add_field(
                name=(
                    "Subcommands:"
                    if len(pagified_str) == 1
                    else f"Subcommands ({index}/{len(pagified_str)}):"
                ),
                value=page,
                inline=False,
            )
            new_embed.set_footer(
                text=(
                    f"Page ({index}/{len(pagified_str)}) | Use {self.context.clean_prefix}help <cog_or_command> for more info on a cog or command."
                    if len(pagified_str) > 1
                    else f"Use {self.context.clean_prefix}help <cog_or_command> for more info on a cog or command."
                )
            )
            embeds.append(new_embed)

        return embeds

    def format_commands(self, command_list: List[commands.Command]) -> str:
        final = ""

        for command in command_list:
            desc = f"`{command.name:<{self.COMMAND_NAME_WIDTH}}:` {self.command_description(command).splitlines()[0]}".replace(
                "[p]", self.context.clean_prefix
            ).replace(
                "[bot]", self.context.bot.user.name
            )
            if len(desc) >= 57:
                desc = f"{desc[:57]}...\n"
            else:
                desc += "\n"

            final += desc

        return final

    def split_command_field_embed(
        self, embed: discord.Embed, command_str: str
    ) -> List[discord.Embed]:
        pagified_str: List[str] = pagify(command_str, delims=["\n"], page_length=512)

        embeds: List[discord.Embed] = []

        for index, page in enumerate(pagified_str, 1):
            new_embed = discord.Embed.from_dict(embed.to_dict())
            new_embed.add_field(
                name=(
                    "Commands:"
                    if len(pagified_str) == 1
                    else f"Commands ({index}/{len(pagified_str)}):"
                ),
                value=page,
                inline=False,
            )
            new_embed.set_footer(
                text=(
                    f"Page ({index}/{len(pagified_str)}) | Use {self.context.clean_prefix}help <cog_or_command> for more info on a cog or command."
                    if len(pagified_str) > 1
                    else f"Use {self.context.clean_prefix}help <cog_or_command> for more info on a cog or command."
                )
            )
            embeds.append(new_embed)

        return embeds

    def new_help_embed(self) -> discord.Embed:
        name = (
            (self.context.guild.me.nick or self.context.bot.user.name)
            if self.context.guild
            else self.context.bot.user.name
        )
        embed = discord.Embed(colour=self.context.bot.colour)
        embed.set_author(
            name=f"{name} Help Menu",
            icon_url=self.context.bot.user.display_avatar,
        )
        return embed

    async def build_bot_help_pages(
        self, cog_list: List[commands.Cog]
    ) -> List[discord.Embed]:
        pages: List[discord.Embed] = []
        current = self.new_help_embed()

        for cog in sorted(cog_list, key=lambda c: c.qualified_name.lower()):
            commands_list = await self.filter_commands(cog.get_commands(), sort=True)
            if not commands_list:
                continue

            command_text = self.format_commands(commands_list).strip()
            chunks = pagify(
                command_text or "No commands available.",
                delims=["\n"],
                page_length=512,
            )

            for index, chunk in enumerate(chunks, 1):
                if len(current.fields) >= 5:
                    pages.append(current)
                    current = self.new_help_embed()

                field_name = (
                    f"{cog.qualified_name} ({index}/{len(chunks)})"
                    if len(chunks) > 1
                    else cog.qualified_name
                )
                current.add_field(name=field_name, value=chunk, inline=False)

        if current.fields:
            pages.append(current)
        return pages

    def add_bot_help_footers(
        self, embed_pages: List[discord.Embed]
    ) -> List[discord.Embed]:
        footer = f"Use {self.context.clean_prefix}help <cog_or_command> for more info on a cog or command."
        return [
            discord.Embed.from_dict(embed.to_dict()).set_footer(
                text=(
                    footer
                    if len(embed_pages) == 1
                    else f"Page ({index}/{len(embed_pages)}) | {footer}"
                )
            )
            for index, embed in enumerate(embed_pages, 1)
        ]

    async def send_bot_help(self, mapping: Mapping[Any, Any]) -> None:
        cog_list = [cog for cog in mapping if cog is not None]
        if not cog_list:
            embed = discord.Embed(
                description="No cogs found.",
                colour=self.context.bot.colour,
            )
            embed.set_footer(
                text=f"Use {self.context.clean_prefix}help <cog_or_command> "
                "for more info on a cog or command."
            )
            await PaginatorView(self.context, [embed], timeout=60.0).start()
            return

        pages = await self.build_bot_help_pages(cog_list) or [
            discord.Embed(
                description="No available commands found.",
                colour=self.context.bot.colour,
            )
        ]

        final_embeds = self.add_bot_help_footers(pages)
        await PaginatorView(self.context, final_embeds, timeout=60.0).start()

    async def send_cog_help(self, cog: commands.Cog) -> None:
        command_list = await self.filter_commands(cog.get_commands(), sort=True)
        prefix = self.context.clean_prefix
        description = inspect.cleandoc(cog.description or "No description provided.")
        description_lines = (
            description.replace("[p]", prefix)
            .replace("[bot]", self.context.bot.user.name)
            .splitlines()
        )
        if description_lines:
            description_lines[0] = f"**{description_lines[0]}**"
        description = "\n".join(description_lines).strip()

        embed = discord.Embed(
            description=description,
            colour=self.context.bot.colour,
        )
        name = (
            (self.context.guild.me.nick or self.context.bot.user.name)
            if self.context.guild
            else self.context.bot.user.name
        )
        embed.set_author(
            name=f"{name} Help Menu", icon_url=self.context.bot.user.display_avatar
        )
        embed.set_footer(
            text=f"Use {self.context.clean_prefix}help <cog_or_command> for more info on a cog or command."
        )

        if not command_list:
            await PaginatorView(self.context, [embed], timeout=60.0).start()
            return

        command_text = self.format_commands(command_list)
        pages = self.split_command_field_embed(embed, command_text)
        await PaginatorView(self.context, pages, timeout=60.0).start()

    async def send_command_help(
        self, command: Union[commands.Command, commands.Group]
    ) -> None:
        prefix = self.context.clean_prefix
        desc = (
            f"```properties\nUsage: {prefix}{command.qualified_name} {command.signature.replace(']...', '...]')}\n"
            f"{f'Aliases: {format_list(list(command.aliases))}\n' if command.aliases else ''}```"
        )

        init_cmd_desc = self.command_description(command)
        cmd_descs = init_cmd_desc.splitlines()
        desc += f"**{cmd_descs.pop(0)}**\n".replace("[p]", prefix).replace(
            "[bot]", self.context.bot.user.name
        )
        desc += (
            "\n".join(cmd_descs)
            .replace("[p]", prefix)
            .replace("[bot]", self.context.bot.user.name)
            .strip()
            or "\n"
        )

        embed = discord.Embed(
            description=desc,
            colour=self.context.bot.colour,
        )
        name = (
            (self.context.guild.me.nick or self.context.bot.user.name)
            if self.context.guild
            else self.context.bot.user.name
        )
        embed.set_author(
            name=f"{name} Help Menu", icon_url=self.context.bot.user.display_avatar
        )
        embed.set_footer(
            text=f"Use {self.context.clean_prefix}help <cog_or_command> for more info on a cog or command."
        )
        if bp := self.get_bot_permissions(command):
            embed.add_field(name="Bot Permissions:", value=bp, inline=False)
        if up := self.get_user_permissions(command):
            embed.add_field(name="User Permissions:", value=up, inline=False)
        if cd := self.get_command_cooldown_and_max_concurrency(command):
            embed.add_field(name="Cooldown:", value=cd, inline=False)

        await PaginatorView(self.context, [embed], 60.0).start()

    async def send_group_help(self, group: commands.Group) -> None:
        command_list = await self.filter_commands(group.commands, sort=True)

        if not command_list:
            await self.send_command_help(group)
            return

        prefix = self.context.clean_prefix
        desc = (
            f"```properties\nUsage: {prefix}{group.qualified_name} {group.signature}\n"
            f"{f'Aliases: {format_list(list(group.aliases))}\n' if group.aliases else ''}```"
        )

        init_cmd_desc = self.command_description(group)
        cmd_descs = init_cmd_desc.splitlines()
        desc += f"**{cmd_descs.pop(0)}**\n".replace("[p]", prefix).replace(
            "[bot]", self.context.bot.user.name
        )
        desc += (
            "\n".join(cmd_descs)
            .replace("[p]", prefix)
            .replace("[bot]", self.context.bot.user.name)
            .strip()
            or "\n"
        )

        embed = discord.Embed(
            description=desc,
            colour=self.context.bot.colour,
        )
        name = (
            (self.context.guild.me.nick or self.context.bot.user.name)
            if self.context.guild
            else self.context.bot.user.name
        )
        embed.set_author(
            name=f"{name} Help Menu", icon_url=self.context.bot.user.display_avatar
        )
        embed.set_footer(
            text=f"Use {self.context.clean_prefix}help <cog_or_command> for more info on a cog or command."
        )

        if bp := self.get_bot_permissions(group):
            embed.add_field(name="Bot Permissions:", value=bp, inline=False)
        if up := self.get_user_permissions(group):
            embed.add_field(name="User Permissions:", value=up, inline=False)
        if cd := self.get_command_cooldown_and_max_concurrency(group):
            embed.add_field(name="Cooldown:", value=cd, inline=False)

        await PaginatorView(
            self.context,
            self.split_subcommand_embed(embed, self.format_commands(command_list)),
            timeout=60.0,
        ).start()

    async def send_error_message(self, error: str) -> None:
        embed = discord.Embed(
            description=error,
            colour=self.context.bot.colour,
        )
        embed.set_author(
            name=f"{(self.context.guild.me.nick or self.context.bot.user.name) if self.context.guild else self.context.bot.user.name} Help Menu",
            icon_url=self.context.bot.user.display_avatar,
        )
        embed.set_footer(
            text=f"Use {self.context.clean_prefix}help <cog_or_command> for more info on a cog or command."
        )
        await self.get_destination().send(embed=embed)

    def command_not_found(self, string: str) -> str:
        return f'No command called `"{string}"` found.'

    def subcommand_not_found(
        self, command: commands.Command[Any, ..., Any], string: str, /
    ) -> str:
        if isinstance(command, commands.Group) and len(command.all_commands) > 0:
            return (
                f'Command `"{command.qualified_name}"` has no subcommand named **{string}**'
            )
        return f'Command `"{command.qualified_name}"` has no subcommands.'
