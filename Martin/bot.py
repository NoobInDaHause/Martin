import contextlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Union, cast

import aiohttp
import discord
from discord.ext import commands
from discord.utils import MISSING
from packaging.version import Version

from Utilities.formatting import format_list, format_time
from .help_command import MartinHelpCommand
from .settings import PROJECT_ROOT, Settings

GITHUB_REPOSITORY = "NoobInDaHause/Martin"

if TYPE_CHECKING:
    from .context import MartinContext


def _prefix_callable(bot: "Martin", message: discord.Message) -> List[str]:
    """A callable that returns the prefix for a given message."""
    return bot._get_prefix(message)


class Martin(commands.AutoShardedBot):
    """
    Martin Bot.
    """

    def __init__(self, settings: Settings):
        super().__init__(
            command_prefix=_prefix_callable,
            intents=discord.Intents.all(),
            help_command=MartinHelpCommand(),
            description="A Discord bot/app written in Python.",
        )
        self.default_prefixes = settings.default_prefixes
        self.guild_prefixes = settings.guild_prefixes
        self.blacklisted_user_ids = settings.blacklisted_user_ids
        self.global_hex_colour = settings.global_hex_colour
        self.uptime = datetime.now(timezone.utc)
        self.log = logging.getLogger("Martin")
        self.exit_code = 0

    @property
    def __version__(self) -> str:
        return (PROJECT_ROOT / "version.txt").read_text(encoding="utf-8").strip()

    @property
    def colour(self) -> discord.Colour:
        return discord.Colour.from_str(self.global_hex_colour)

    @property
    def color(self) -> discord.Colour:
        return self.colour

    def _get_prefix(self, message: discord.Message) -> List[str]:
        """Get the prefix for a given message."""
        if message.guild is None:
            return self.default_prefixes
        return self.guild_prefixes.get(str(message.guild.id), self.default_prefixes)

    async def get_updates(self) -> Dict[str, str]:
        """Get the latest GitHub version and compare it with the bot version."""
        releases_url = (
            f"https://api.github.com/repos/{GITHUB_REPOSITORY}/releases/latest"
        )
        latest_version = ""
        release_url = releases_url

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(releases_url) as response:
                    if response.status == 200:
                        release = cast(Dict[str, str], await response.json())
                        latest_version = release.get("tag_name", "")
                        release_url = release.get("html_url", releases_url)
                    elif response.status == 404:
                        tags_url = (
                            f"https://api.github.com/repos/{GITHUB_REPOSITORY}/tags"
                        )
                        async with session.get(tags_url) as tags_response:
                            if tags_response.status != 200:
                                return {
                                    "status": "error",
                                    "message": (
                                        "GitHub returned "
                                        f"HTTP {tags_response.status} while checking tags."
                                    ),
                                }
                            tags = cast(
                                List[Dict[str, str]], await tags_response.json()
                            )
                        if tags:
                            latest_tag = tags[0].get("name", "")
                            latest_version = latest_tag
                            release_url = f"https://github.com/{GITHUB_REPOSITORY}/releases/tag/{latest_tag}"
                    else:
                        return {
                            "status": "error",
                            "message": (
                                "GitHub returned "
                                f"HTTP {response.status} while checking updates."
                            ),
                        }
        except aiohttp.ClientError:
            return {
                "status": "error",
                "message": "Unable to connect to GitHub while checking for updates.",
            }

        current_version = str(self.__version__)
        if not latest_version:
            return {"status": "error", "message": "GitHub did not provide a version."}

        return {
            "status": (
                "update_available"
                if Version(latest_version) > Version(current_version)
                else "up_to_date"
            ),
            "current_version": current_version,
            "latest_version": latest_version,
            "release_url": release_url,
        }

    async def setup_hook(self) -> None:
        await super().setup_hook()
        app_info = await self.application_info()
        members = app_info.team.members if app_info.team else [app_info.owner]
        self.owner_ids = {member.id for member in members}

        cogs_path = Path(__file__).parents[1] / "Cogs"
        for cog_folder in cogs_path.iterdir():
            if cog_folder.is_dir() and (cog_folder / "__init__.py").is_file():
                await self.load_extension(f"Cogs.{cog_folder.name}")

        cog_names = list(self.cogs)
        if cog_names:
            plural = "s" if len(cog_names) > 1 else ""
            self.log.info("Loaded cog%s: %s", plural, format_list(cog_names))

        self.log.info("Logged in as %s (ID: %s).", self.user, self.user.id)
        self.log.info("--------------------------------------------------")

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if self.is_blacklisted(message.author) and not await self.is_owner(
            message.author
        ):
            return
        await self.process_commands(message)

    async def on_command_error(
        self, context: "MartinContext", error: commands.CommandError
    ) -> None:
        if isinstance(error, (commands.CommandNotFound, commands.DisabledCommand)):
            return

        if isinstance(error, commands.CommandOnCooldown):
            msg = await context.send(
                f"This command is on cooldown. Try again in **{format_time(error.retry_after)}**."
            )
            with contextlib.suppress(discord.errors.NotFound):
                await msg.delete(delay=error.retry_after)
            return

        if isinstance(error, commands.MissingRequiredArgument):
            await context.send_help(context.command)
            return

        if isinstance(error, commands.MissingPermissions):
            permissions = format_list(error.missing_permissions)
            await context.send(f"You need these permissions: {permissions}.")
            return

        if isinstance(error, commands.BotMissingPermissions):
            permissions = format_list(error.missing_permissions)
            await context.send(f"I need these permissions: {permissions}.")
            return

        if isinstance(error, commands.NotOwner):
            self.log.info(
                "User %s tried to run an owner only command. Command: %s",
                context.author,
                context.command.qualified_name,
            )
            return

        if isinstance(error, commands.NoPrivateMessage):
            await context.send("That command cannot be used in private messages.")
            return

        if isinstance(error, commands.MaxConcurrencyReached):
            await context.send("That command is already running. Try again later.")
            return

        if isinstance(error, commands.BadArgument):
            await context.send(content=str(error))
            return

        is_this_guy_owner = (
            "Check your console or logs for details."
            if await self.is_owner(context.author)
            else ""
        )
        if isinstance(error, commands.CommandInvokeError):
            original = error.original
            self.log.error(
                "Command %s failed.",
                context.command,
                exc_info=(type(original), original, original.__traceback__),
            )
            await context.send(
                f"Error in command `'{context.command}'`. {is_this_guy_owner}"
            )
            return

        self.log.error("Unhandled command error in %s: %s", context.command, error)
        await context.send(
            f"Error in command `'{context.command}'`. {is_this_guy_owner}"
        )

    async def get_context(self, origin, /, *, cls=MISSING) -> "MartinContext":
        return await super().get_context(origin, cls=cls)

    async def get_or_fetch_user(self, user_id: int) -> discord.User:
        return self.get_user(user_id) or await self.fetch_user(user_id)

    async def send_to_owners(self, *args, **kwargs) -> None:
        for o_id in self.owner_ids:
            with contextlib.suppress(
                discord.errors.Forbidden,
                discord.errors.NotFound,
                discord.errors.HTTPException,
            ):
                await (await self.get_or_fetch_user(o_id)).send(*args, **kwargs)

    def is_blacklisted(
        self, user_or_user_id: Union[discord.Member, discord.User, int]
    ) -> bool:
        return (
            getattr(user_or_user_id, "id", user_or_user_id) in self.blacklisted_user_ids
        )

    async def close(self, restart: bool = False) -> None:
        if restart:
            self.exit_code = 26

        self.log.info(
            "Cleaning up before %s.", ("shutting down" if not restart else "restarting")
        )
        return await super().close()
