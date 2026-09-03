import copy
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import List, Tuple

import discord
from discord import app_commands
from discord.ext import commands

from Martin import Martin, MartinInteraction
from Utilities.formatting import pagify
from Utilities.views import ConfirmationView, PaginatorView

from .views import OwnerView


class Owner(commands.Cog):
    """
    Owner only.

    No peasants allowed.
    """

    def __init__(self, bot: Martin):
        self.bot = bot

    @staticmethod
    def cog_exists(cog_name: str) -> bool:
        cogs_path = Path(__file__).parents[2] / "Cogs"
        return (cogs_path / cog_name).is_dir() and (
            cogs_path / cog_name / "__init__.py"
        ).is_file()

    async def manage_cog(self, action: str, cog_name: str) -> Tuple[bool, str]:
        extension = f"Cogs.{cog_name}"
        try:
            if action == "load":
                await self.bot.load_extension(extension)
            elif action == "unload":
                await self.bot.unload_extension(extension)
            else:
                await self.bot.reload_extension(extension)
        except commands.ExtensionNotFound:
            return False, "extension not found"
        except commands.ExtensionAlreadyLoaded:
            return False, "already loaded"
        except commands.ExtensionNotLoaded:
            return False, "not loaded"
        except commands.ExtensionFailed as error:
            return False, str(error)

        return True, ""

    async def manage_cogs(
        self, interaction: MartinInteraction, action: str, cog_names: List[str]
    ) -> None:
        protected = [
            cog_name for cog_name in cog_names if cog_name.casefold() == "owner"
        ]
        missing = [cog_name for cog_name in cog_names if not self.cog_exists(cog_name)]
        existing = [
            cog_name
            for cog_name in cog_names
            if cog_name not in missing and cog_name not in protected
        ]
        results = [
            (cog_name, await self.manage_cog(action, cog_name)) for cog_name in existing
        ]
        successful = [cog_name for cog_name, (succeeded, _) in results if succeeded]
        failed = [
            (cog_name, reason)
            for cog_name, (succeeded, reason) in results
            if not succeeded
        ]
        messages = []
        verb = f"{action}ed"
        if successful:
            cog_label = "cog" if len(successful) == 1 else "cogs"
            messages.append(
                f"{verb.capitalize()} {cog_label}: {discord.utils._human_join(successful, final='and')}"
            )
        if failed:
            cog_label = "cog" if len(failed) == 1 else "cogs"
            failed_details = discord.utils._human_join(
                [f"{cog_name} ({reason})" for cog_name, reason in failed], final="and"
            )
            messages.append(
                f"The following {cog_label} failed to {action}: {failed_details}"
            )
        if missing:
            cog_label = "cog" if len(missing) == 1 else "cogs"
            exist_verb = "does not exist" if len(missing) == 1 else "do not exist"
            messages.append(
                f"The following {cog_label} {exist_verb}: {discord.utils._human_join(missing, final='and')}"
            )
        if protected:
            cog_label = "cog" if len(protected) == 1 else "cogs"
            messages.append(
                f"The following {cog_label} cannot be {verb}: {discord.utils._human_join(protected, final='and')}"
            )
        await interaction.response_or_followup(content="\n".join(messages))

    async def restart_or_shutdown(
        self, interaction: MartinInteraction, restart: bool
    ) -> None:
        done_msg = (
            "Restarting... :arrows_counterclockwise:"
            if restart
            else "Shutting down. :wave:"
        )
        confirm_view = ConfirmationView(interaction, done_msg)

        await confirm_view.start(
            content=f"Are you sure you want me to {'restart' if restart else 'shutdown'}?",
            view=confirm_view,
        )
        await confirm_view.wait()

        if confirm_view.value:
            confirm_view.stop()
            await interaction.client.close(restart)

    async def _guilds(self, interaction: MartinInteraction) -> None:
        guilds: List[discord.Guild] = sorted(
            self.bot.guilds, key=lambda g: g.member_count, reverse=True
        )
        guild_list = "\n".join(
            f"{index}. **{guild.name}** (`{guild.id}`) - {guild.member_count} members"
            for index, guild in enumerate(guilds, start=1)
        )

        pagified_guilds = pagify(guild_list)

        if len(pagified_guilds) == 1:
            guild_len = len(guilds)
            embed = discord.Embed(
                title=f"{self.bot.user.name} is in `{guild_len}` guild{'' if guild_len == 1 else 's'}.",
                description=pagified_guilds[0],
                colour=self.bot.colour,
                timestamp=datetime.now(timezone.utc),
            )
            await interaction.response_or_followup(embed=embed)
        else:
            embeds = [
                discord.Embed(
                    title=f"{self.bot.user.name} is in `{len(guilds)}` guilds.",
                    description=page,
                    colour=self.bot.colour,
                    timestamp=datetime.now(timezone.utc),
                ).set_footer(text=f"Page ({index}/{len(pagified_guilds)})")
                for index, page in enumerate(pagified_guilds, start=1)
            ]

            await PaginatorView(interaction, embeds).start()

    async def _cog_list(self, interaction: MartinInteraction) -> None:
        cogs_path = Path(__file__).parents[2]
        cog_names = sorted(
            cog_folder.name
            for cog_folder in (cogs_path / "Cogs").iterdir()
            if cog_folder.is_dir() and (cog_folder / "__init__.py").is_file()
        )
        loaded = [
            cog_name
            for cog_name in cog_names
            if f"Cogs.{cog_name}" in self.bot.extensions
        ]
        unloaded = [cog_name for cog_name in cog_names if cog_name not in loaded]

        def format_cogs(names: List[str]) -> str:
            return "\n".join(f"- `{name}`" for name in names) or "- None"

        markdown = (
            "# Cogs\n\n"
            f"## Loaded ({len(loaded)})\n\n"
            f"{format_cogs(loaded)}\n\n"
            f"## Unloaded ({len(unloaded)})\n\n"
            f"{format_cogs(unloaded)}\n"
        )
        cog_file = discord.File(BytesIO(markdown.encode("utf-8")), filename="cogs.md")
        await interaction.response_or_followup(file=cog_file)

    async def _colour(self, interaction: MartinInteraction, colour: str = None):
        colour = colour or "#276a8a"
        dc = discord.Colour.from_str(colour)
        self.bot.global_hex_colour = str(dc)
        embed = discord.Embed(
            description=f"Successfully changed bot colour to {dc}.",
            colour=self.bot.colour,
        )
        self.bot.save_settings()
        await interaction.response_or_followup(embed=embed)

    @app_commands.command(name="owner", description="Owner only commands.")
    @app_commands.checks.is_owner()
    @app_commands.checks.bot_has_permissions(attach_files=True, embed_links=True)
    @app_commands.describe(
        command="The owner command to execute.",
        argument="An optional argument for the command.",
    )
    async def owner(
        self, interaction: MartinInteraction, command: str, argument: str = None
    ) -> None:
        """
        No peasants allowed.
        """
        desc = """
            Command names highlighted as bold require an argument.
            
            Available owner commands:
            > restart: Restarts the bot.
            Usage: /owner command:restart
            > shutdown: Shuts down the bot.
            Usage: /owner command:shutdown
            > guilds: Shows the list of guilds the bot is in.
            Usage: /owner command:guilds
            > **loadcog**: Loads a cog. Separate cog names with spaces.
            Usage: /owner command:loadcog argument:<cog_names...>
            > **unloadcog**: Unloads a cog. Separate cog names with spaces.
            Usage: /owner command:unloadcog argument:<cog_names...>
            > **reloadcog**: Reloads a cog. Separate cog names with spaces.
            Usage: /owner command:reloadcog argument:<cog_names...>
            > coglist: Shows the list of loaded/unloaded cogs.
            Usage: /owner command:coglist
            > **botcolour**: Change the bot global embed hex colour, leave argument blank to set it back to default.
            Usage: /owner command:botcolour argument:[hex_code]
            Aliases: botcolor
            """
        embed = discord.Embed(
            title="Owner command pannel", description=desc, colour=self.bot.colour
        )

        await OwnerView(self, interaction).start(embed=embed)

    # async def _set_blacklist(self, ctx: commands.Context):
    #     """
    #     Base commands for blacklisting users.

    #     Shows who are in the naughty list.
    #     """
    #     blacklisted = []

    #     for x in self.bot.blacklisted_user_ids:
    #         user = await self.bot.get_or_fetch_user(x)
    #         if user is None:
    #             blacklisted.append(f"**Unknown User** (`{x}`)")
    #         else:
    #             blacklisted.append(f"**{user}** (`{user.id}`)")

    #     embed = discord.Embed(
    #         title="List of users in the naughty list.",
    #         description="\n".join(blacklisted) or "No users in the naughty list.",
    #         colour=self.bot.colour,
    #     )
    #     await ctx.send(embed=embed)

    # async def blacklist_add(
    #     self, ctx: commands.Context, users: commands.Greedy[discord.User]
    # ):
    #     """
    #     Add users to the [bot]'s blacklist.

    #     Can not add bots or bot owners or users already in blacklist to the blacklist.
    #     """
    #     added = []
    #     failed = []
    #     if not users:
    #         return await ctx.send_help()

    #     for user in users:
    #         if (
    #             await self.bot.is_owner(user)
    #             or user.bot
    #             or self.bot.is_blacklisted(user)
    #         ):
    #             failed.append(f"**{user.name}** (`{user.id}`)")
    #             continue
    #         self.bot.blacklisted_user_ids.append(user.id)
    #         added.append(f"**{user.name}** (`{user.id}`)")

    #     if added:
    #         self.bot.save_settings()
    #         await ctx.send(
    #             content=f"Blacklisted {discord.utils._human_join(added, final='and')}."
    #         )
    #     if failed:
    #         await ctx.send(
    #             content=f"Failed to blacklist {discord.utils._human_join(failed, final='and')} since they are likely to be a bot, bot owner, or already blacklisted."
    #         )

    # async def blacklist_remove(
    #     self, ctx: commands.Context, users: commands.Greedy[discord.User]
    # ):
    #     """
    #     Remove users from the [bot]'s blacklist.

    #     Can not remove users from the blacklist if they are not blacklisted.
    #     """
    #     removed = []
    #     failed = []
    #     if not users:
    #         return await ctx.send_help()

    #     for user in users:
    #         if (
    #             await self.bot.is_owner(user)
    #             or user.bot
    #             or not self.bot.is_blacklisted(user)
    #         ):
    #             failed.append(f"**{user.name}** (`{user.id}`)")
    #             continue
    #         self.bot.blacklisted_user_ids.remove(user.id)
    #         removed.append(f"**{user.name}** (`{user.id}`)")

    #     if removed:
    #         self.bot.save_settings()
    #         await ctx.send(
    #             content=f"Unblacklisted {discord.utils._human_join(removed, final='and')}."
    #         )
    #     if failed:
    #         await ctx.send(
    #             content=f"Failed to unblacklist {discord.utils._human_join(failed, final='and')} since they are likely to be a bot, bot owner, or already blacklisted."
    #         )
