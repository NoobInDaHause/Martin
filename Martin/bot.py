import contextlib
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Union, cast

import aiohttp
import discord
from discord.ext import commands
from discord.utils import MISSING
from packaging.version import Version

from Utilities.formatting import format_list, format_time
from .context import MartinContext
from .help_command import MartinHelpCommand
from .settings import PROJECT_ROOT, Settings
from .tree import MartinTree

GITHUB_REPOSITORY = "NoobInDaHause/Martin"
HELP_COMMAND_ATTRS = {
    "cooldown": commands.CooldownMapping.from_cooldown(
        1, 3.0, commands.BucketType.user
    ),
    "help": (
        "Shows help about the bot, command or cog.\n\n"
        "Ich brauche hier etwas Hilfe.\n"
        "Trenger litt hjelp her.\n"
        "J'ai besoin d'aide."
    ),
    "hidden": True,
    "aliases": ["h", "hilfe", "hjelp", "cananyonehelpme"],
}


def _prefix_callable(bot: "Martin", message: discord.Message) -> List[str]:
    """A callable that returns the prefix for a given message."""
    default_prefixes = bot.default_prefixes
    guild_id = str(message.guild.id) if message.guild else None
    if guild_id:
        guild_prefixes = bot.guild_prefixes.get(guild_id, default_prefixes)
    else:
        guild_prefixes = default_prefixes
    prefixes = []
    prefixes.extend(guild_prefixes)
    return list(dict.fromkeys(prefixes).keys())


class Martin(commands.AutoShardedBot):
    """
    Martin Bot.
    """

    def __init__(self, settings: Settings):
        super().__init__(
            command_prefix=_prefix_callable,
            intents=discord.Intents.all(),
            help_command=MartinHelpCommand(command_attrs=HELP_COMMAND_ATTRS),
            description="A Discord bot/app written in Python.",
            tree_cls=MartinTree
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

    def _get_guild_prefix(self, guild: discord.Guild) -> List[str]:
        """Get the prefix for a given message."""
        return self.guild_prefixes.get(str(guild.id), self.default_prefixes)

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

        if not latest_version:
            return {"status": "error", "message": "GitHub did not provide a version."}

        return {
            "status": (
                "update_available"
                if Version(latest_version) > Version(self.__version__)
                else "up_to_date"
            ),
            "current_version": self.__version__,
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

        if cog_names := list(self.cogs):
            plural = "s" if len(cog_names) > 1 else ""
            self.log.info("Loaded cog%s: %s", plural, format_list(cog_names))

        self.log.info("Logged in as %s (ID: %s).", self.user, self.user.id)
        self.log.info("--------------------------------------------------")

        update = await self.get_updates()
        self.log.info("Checking for Martin updates.")
        if update["status"] == "error":
            self.log.warning(update["message"])
        elif update["status"] == "update_available":
            self.log.info(
                f"Update detected: `{update['current_version']}` -> `{update['latest_version']}`"
            )
            embed = discord.Embed(
                title="Hey there :wave:. I have detected a newer version of Martin on GitHub.",
                description=(
                    f"`{update['current_version']}` -> `{update['latest_version']}`\n"
                    f"[View release]({update['release_url']})"
                ),
                colour=self.colour,
                timestamp=discord.utils.utcnow(),
            )
            await self.send_to_owners(
                embed=embed,
            )
        else:
            self.log.info("Martin is up to date.")

    async def invoke(self, ctx: MartinContext, /) -> None:
        if self.is_blacklisted(ctx.author):
            self.log.info(
                "User %s (%s) is blacklisted and tried to run command '%s' in channel #%s (%s).",
                ctx.author,
                ctx.author.id,
                ctx.command.qualified_name if ctx.command else "N/A",
                "DM Channel" if isinstance(ctx.channel, discord.DMChannel) else ctx.channel,
                ctx.channel.id,
            )
            return
        return await super().invoke(ctx)

    async def on_command_error(
        self, context: MartinContext, error: commands.CommandError
    ) -> None:
        is_this_guy_owner = (
            "Check your console or logs for details."
            if await self.is_owner(context.author)
            else ""
        )

        error_msg = f"Error in command `'{context.command}'`. {is_this_guy_owner}"
        
        if isinstance(error, (commands.CommandNotFound, commands.DisabledCommand)):
            return
        elif isinstance(error, commands.CommandOnCooldown):
            time_left = datetime.now(timezone.utc) + timedelta(seconds=error.retry_after)
            msg = await context.send(
                f"This command is on cooldown. Try again in <t:{int(time_left.timestamp())}:R>."
            )
            with contextlib.suppress(discord.errors.NotFound):
                await msg.delete(delay=error.retry_after)
        elif isinstance(error, commands.MissingRequiredArgument):
            await context.send_help()
        elif isinstance(error, commands.MissingPermissions):
            permissions = format_list(error.missing_permissions)
            await context.send(f"You need these permissions: {permissions}.")
        elif isinstance(error, commands.BotMissingPermissions):
            permissions = format_list(error.missing_permissions)
            await context.send(f"I require these permissions: {permissions}.")
        elif isinstance(error, commands.NotOwner):
            self.log.info(
                "User %s (%s) tried to run an owner only command in channel #%s (%s). Command: '%s'",
                context.author,
                context.author.id,
                context.channel,
                context.channel.id,
                context.command.qualified_name,
            )
        elif isinstance(error, commands.NoPrivateMessage):
            await context.send("This command can only be used in guilds.")
        elif isinstance(error, commands.MaxConcurrencyReached):
            await context.send(
                "Command max concurrecy reached, please wait for the previous command to finish."
            )
        elif isinstance(error, commands.BadArgument):
            await context.send(content=str(error))
        elif isinstance(error, commands.CommandInvokeError):
            self.log.error(
                "Command %s failed.",
                context.command,
                exc_info=(type(error), error, error.__traceback__),
            )
            await context.send(error_msg)
        elif isinstance(error, commands.NSFWChannelRequired):
            await context.send(
                content="This command can only be used in a NSFW channel."
            )
        else:
            self.log.error(
                "Unhandled command error in %s",
                context.command.qualified_name,
                exc_info=(type(error), error, error.__traceback__),
            )
            await context.send(error_msg)

    async def get_context(self, origin, /, *, cls=MISSING) -> MartinContext:
        return await super().get_context(origin, cls=MartinContext)

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
            "Cleaning up before %s.", ("restarting" if restart else "shutting down")
        )
        self.save_settings()
        return await super().close()

    def save_settings(self):
        with open(PROJECT_ROOT / "config.json", "w", encoding="utf-8") as conf:
            data = {
                "default_prefixes": self.default_prefixes,
                "guild_prefixes": self.guild_prefixes,
                "global_hex_colour": self.global_hex_colour,
                "blacklisted_user_ids": self.blacklisted_user_ids,
            }
            json.dump(data, conf, indent=4)
