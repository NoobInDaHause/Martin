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

from Utilities.exceptions import UserIsBlacklisted
from .context import MartinContext
from .help_command import MartinHelpCommand
from .interaction import MartinInteraction
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
            tree_cls=MartinTree,
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

    async def naughty_users(self, ctx: MartinContext, /) -> bool:

        if self.is_blacklisted(ctx.author):
            raise UserIsBlacklisted("You are blacklisted from using this bot.")

        return True

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
            self.log.info(
                "Loaded cog%s: %s",
                plural,
                discord.utils._human_join(cog_names, final="and"),
            )

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

        self.add_check(self.naughty_users)

        await super().setup_hook()

    async def on_command_error(
        self, context: MartinContext, exception: commands.CommandError, /
    ) -> None:
        if isinstance(exception, (commands.CommandNotFound, commands.DisabledCommand)):
            return

        await self.handle_command_error(context, exception)

    async def handle_command_error(
        self, context: MartinContext, exception: commands.CommandError, /
    ) -> None:
        owner_message = (
            "Check your console or logs for details."
            if await self.is_owner(context.author)
            else ""
        )
        error_msg = f"Error in command `'{context.command}'`. {owner_message}"

        if isinstance(exception, commands.PrivateMessageOnly):
            await context.send(content=str(exception))
            return

        if isinstance(exception, commands.CommandOnCooldown):
            time_left = datetime.now(timezone.utc) + timedelta(
                seconds=exception.retry_after
            )
            msg = await context.send(
                f"This command is on cooldown. Try again in <t:{int(time_left.timestamp())}:R>."
            )
            with contextlib.suppress(discord.errors.NotFound):
                await msg.delete(delay=exception.retry_after)
            return

        if isinstance(exception, commands.MissingRequiredArgument):
            await context.send_help()
            return

        if isinstance(
            exception, (commands.MissingPermissions, commands.BotMissingPermissions)
        ):
            permissions = discord.utils._human_join(
                [
                    f"`{permission.replace('_', ' ').strip().title()}`"
                    for permission in exception.missing_permissions
                ],
                final="and",
            )
            prefix = (
                "I require these permissions"
                if isinstance(exception, commands.BotMissingPermissions)
                else "You need these permissions"
            )
            await context.send(f"{prefix}: {permissions}.")
            return

        if isinstance(exception, commands.NotOwner):
            self.log.info(
                "User %s (%s) tried to run an owner only command in channel #%s (%s). Command: '%s'",
                context.author,
                context.author.id,
                (
                    "DM Channel"
                    if isinstance(context.channel, discord.DMChannel)
                    else context.channel
                ),
                context.channel.id,
                context.command.qualified_name,
            )
            return

        if isinstance(exception, commands.NoPrivateMessage):
            await context.send("This command can only be used in guilds.")
            return

        if isinstance(
            exception,
            (
                commands.MaxConcurrencyReached,
                commands.BadArgument,
                commands.NSFWChannelRequired,
            ),
        ):
            await context.send(content=str(exception))
            return

        if isinstance(exception, commands.CommandInvokeError):
            self.log.error(
                "Command %s failed.",
                context.command,
                exc_info=(type(exception), exception, exception.__traceback__),
            )
            await context.send(error_msg)
            return

        if isinstance(exception, UserIsBlacklisted):
            self.log.info(
                "User %s (%s) is blacklisted and tried to run command '%s' in channel #%s (%s).",
                context.author,
                context.author.id,
                context.command.qualified_name if context.command else "N/A",
                (
                    "DM Channel"
                    if isinstance(context.channel, discord.DMChannel)
                    else context.channel
                ),
                context.channel.id,
            )
            return

        if isinstance(exception, commands.CheckFailure): # will put this second to last since other checks above inherit from this class
            return # the custom check will handle the sending of error message

        self.log.error(
            "Unhandled command error in %s",
            context.command.qualified_name,
            exc_info=(type(exception), exception, exception.__traceback__),
        )
        await context.send(error_msg)

    async def get_context(
        self, origin: Union[discord.Message, MartinInteraction], /, *, cls=MISSING
    ) -> MartinContext:
        if cls is MISSING:
            cls = MartinContext
        return await super().get_context(origin, cls=cls)

    async def get_or_fetch_user(self, user_id: int) -> discord.User:
        return self.get_user(user_id) or await self.fetch_user(user_id)

    async def get_or_fetch_member(
        self, guild: discord.Guild, user_id: int
    ) -> discord.Member:
        return guild.get_member(user_id) or await guild.fetch_member(user_id)

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
        self.remove_check(self.naughty_users)
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
