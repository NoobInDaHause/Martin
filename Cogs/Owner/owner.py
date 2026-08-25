from io import BytesIO
from pathlib import Path
from typing import List, Tuple

import discord
from discord.ext import commands

from Martin import Martin, MartinContext


class Owner(commands.Cog):
    """
    Owner only.

    No peasants allowed.
    """

    def __init__(self, bot: Martin):
        self.bot = bot

    async def _manage_cog(self, action: str, cog_name: str) -> Tuple[bool, str]:
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

    @staticmethod
    def _cog_exists(cog_name: str) -> bool:
        cogs_path = Path(__file__).parents[2] / "Cogs"
        return (cogs_path / cog_name).is_dir() and (
            cogs_path / cog_name / "__init__.py"
        ).is_file()

    async def _manage_cogs(
        self, ctx: MartinContext, action: str, cog_names: List[str]
    ) -> None:
        protected = [
            cog_name for cog_name in cog_names if cog_name.casefold() == "owner"
        ]
        missing = [cog_name for cog_name in cog_names if not self._cog_exists(cog_name)]
        existing = [
            cog_name
            for cog_name in cog_names
            if cog_name not in missing and cog_name not in protected
        ]
        results = [
            (cog_name, await self._manage_cog(action, cog_name))
            for cog_name in existing
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
            messages.append(f"{verb.capitalize()} {cog_label}: {', '.join(successful)}")
        if failed:
            cog_label = "cog" if len(failed) == 1 else "cogs"
            failed_details = ", ".join(
                f"{cog_name} ({reason})" for cog_name, reason in failed
            )
            messages.append(
                f"The following {cog_label} failed to {action}: {failed_details}"
            )
        if missing:
            cog_label = "cog" if len(missing) == 1 else "cogs"
            exist_verb = "does not exist" if len(missing) == 1 else "do not exist"
            messages.append(
                f"The following {cog_label} {exist_verb}: {', '.join(missing)}"
            )
        if protected:
            cog_label = "cog" if len(protected) == 1 else "cogs"
            messages.append(
                f"The following {cog_label} cannot be {verb}: {', '.join(protected)}"
            )
        await ctx.send("\n".join(messages))

    @commands.is_owner()
    @commands.command(name="checkforupdates")
    @commands.bot_has_permissions(embed_links=True)
    async def checkforupdates(self, ctx: MartinContext):
        """
        Check whether a newer Bot version is available.
        """
        update = await self.bot.get_updates()
        if update["status"] == "error":
            await ctx.send(update["message"])
            return

        current_version = update["current_version"]
        latest_version = update["latest_version"]
        if update["status"] == "update_available":
            embed = discord.Embed(
                title="Update available",
                description=(
                    f"`{current_version}` -> `{latest_version}`\n"
                    f"[View release]({update['release_url']})"
                ),
                colour=self.bot.colour,
            )
        else:
            embed = discord.Embed(
                title="Bot is up to date",
                description=f"Current version: `{current_version}`",
                colour=self.bot.colour,
            )
        await ctx.send(embed=embed)

    @commands.is_owner()
    @commands.command(name="restart")
    async def restart(self, ctx: MartinContext) -> None:
        """Restart the bot process."""
        await ctx.send("Restarting... :arrows_counterclockwise:")
        ctx.bot.exit_code = 26
        await ctx.bot.close()

    @commands.is_owner()
    @commands.command(name="shutdown")
    async def shutdown(self, ctx: MartinContext, silent: bool = False) -> None:
        """
        Shutdown the bot.

        Silently or not.
        """
        if not silent:
            await ctx.send("Shutting down. :wave:")
        ctx.bot.exit_code = 0
        await ctx.bot.close()

    @commands.is_owner()
    @commands.group(name="cog", invoke_without_command=True)
    async def _cog(self, ctx: MartinContext):
        """
        Base commands for managing cogs.
        """
        return await ctx.send_help(ctx.command)

    @commands.is_owner()
    @_cog.command(name="list")
    @commands.bot_has_permissions(attach_files=True)
    async def _cog_list(self, ctx: MartinContext):
        """
        Shows the list of loaded/unloaded cogs.
        """
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
        await ctx.send(file=cog_file)

    @commands.is_owner()
    @_cog.command(name="load")
    async def _cog_load(
        self, ctx: MartinContext, cog_names: commands.Greedy[commands.clean_content]
    ) -> None:
        """Load one or more cog extensions."""
        if not cog_names:
            await ctx.send_help()
            return
        await self._manage_cogs(ctx, "load", cog_names)

    @commands.is_owner()
    @_cog.command(name="unload")
    async def _cog_unload(
        self, ctx: MartinContext, cog_names: commands.Greedy[commands.clean_content]
    ) -> None:
        """Unload one or more cog extensions."""
        if not cog_names:
            await ctx.send_help()
            return
        await self._manage_cogs(ctx, "unload", cog_names)

    @commands.is_owner()
    @_cog.command(name="reload")
    async def _cog_reload(
        self, ctx: MartinContext, cog_names: commands.Greedy[commands.clean_content]
    ) -> None:
        """Reload one or more cog extensions."""
        if not cog_names:
            await ctx.send_help()
            return
        await self._manage_cogs(ctx, "reload", cog_names)
