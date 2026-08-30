import platform
from datetime import datetime, timezone
from time import perf_counter
from typing import Optional

import discord
from discord.ext import commands

from Martin import Martin, MartinContext
from Utilities.formatting import format_time

from .general_data_manager import GeneralDB


class General(commands.Cog):
    """
    General Cog.

    Various general commands for your needs.
    """

    def __init__(self, bot: Martin):
        self.bot = bot
        self.db = GeneralDB(self.__class__.__name__)

    async def cog_load(self) -> None:
        await self.db.initialize()

    @staticmethod
    def latency_colour(latency_ms: float) -> discord.Colour:
        if latency_ms < 100:
            return discord.Colour.green()
        if latency_ms < 250:
            return discord.Colour.yellow()
        return discord.Colour.red()

    @commands.command(name="uptime")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def uptime(self, ctx: MartinContext) -> None:
        """
        Check how long the bot has been up.
        """
        elapsed_seconds = int(
            (datetime.now(timezone.utc) - self.bot.uptime).total_seconds()
        )
        startup_timestamp = int(self.bot.uptime.timestamp())
        embed = discord.Embed(
            title="Bot uptime",
            description=(
                f"{format_time(elapsed_seconds)}\nStarted <t:{startup_timestamp}:R>"
            ),
            colour=self.bot.colour,
            timestamp=datetime.now(timezone.utc),
        )
        await ctx.send(embed=embed)

    @commands.command(name="ping")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ping(self, ctx: MartinContext) -> None:
        """
        Ping.

        Pong.
        """
        send_started = perf_counter()
        initial_message = await ctx.send(content="Pinging...")
        send_latency = (perf_counter() - send_started) * 1000

        edit_started = perf_counter()
        heartbeat_latency = self.bot.latency * 1000
        measuring_embed = discord.Embed(
            title=":ping_pong: Pong!",
            colour=self.latency_colour(heartbeat_latency),
        )
        measuring_embed.add_field(
            name=f"{self.bot.user} latency",
            value=f"{heartbeat_latency:.2f} ms",
            inline=True,
        )
        measuring_embed.add_field(
            name="Message latency",
            value=f"{send_latency:.2f} ms",
            inline=True,
        )
        measuring_embed.add_field(
            name="Message edit latency",
            value="measuring...",
            inline=True,
        )
        await initial_message.edit(content="", embed=measuring_embed)
        edit_latency = (perf_counter() - edit_started) * 1000

        heartbeat_latency = self.bot.latency * 1000
        result_embed = discord.Embed(
            title=":ping_pong: Pong!",
            colour=self.latency_colour(heartbeat_latency),
        )
        result_embed.add_field(
            name=f"{self.bot.user} latency",
            value=f"{heartbeat_latency:.2f} ms",
            inline=True,
        )
        result_embed.add_field(
            name="Message latency",
            value=f"{send_latency:.2f} ms",
            inline=True,
        )
        result_embed.add_field(
            name="Message edit latency",
            value=f"{edit_latency:.2f} ms",
            inline=True,
        )
        await initial_message.edit(embed=result_embed)

    @commands.command(name="info", aliases=["botinfo"])
    @commands.bot_has_permissions(embed_links=True)
    async def info(self, ctx: MartinContext) -> None:
        """Check info about the bot."""
        async with ctx.typing():
            app_info = await self.bot.application_info()
            owner = f"Team {app_info.team.name}" if app_info.team else app_info.owner
            embed = discord.Embed(
                title=f"{self.bot.user.name} info",
                description=f"Instance owned by `{owner}`.",
                timestamp=datetime.now(timezone.utc),
                colour=self.bot.colour,
            )
            custom_info = (
                f"Instance owned by `{owner}`.\n\n"
                "This bot is an instance of [Martin](https://github.com/NoobInDaHause/Martin) an open source discord ~~bot~~ APP "
                "written in Python. Make one yourself today."
            )
            if c_i := await self.db.get_or_delete_custom_info(False):
                custom_info += f"\n\n{c_i}"

            embed.description = custom_info
            embed.set_thumbnail(url=self.bot.user.display_avatar)

            embed.add_field(
                name="Discord.py Version:", value=discord.__version__, inline=True
            )
            embed.add_field(
                name="Python Version:", value=platform.python_version(), inline=True
            )
            embed.add_field(name="Martin Version:", value=self.bot.__version__, inline=True)

            update = await self.bot.get_updates()
            if update["status"] == "error":
                nam = "GitHub:"
                ver = "Failed to check for updates."
            elif update["status"] == "update_available":
                nam = "New Martin Version:"
                ver = update['latest_version']
            else:
                nam = "GitHub:"
                ver = "Martin is up to date."
            embed.add_field(name=nam, value=ver, inline=True)

            await ctx.send(embed=embed)

    @commands.command(name="invite")
    async def invite(self, ctx: MartinContext) -> None:
        """
        Invite the bot.
        """
        await ctx.send(
            content=f"https://discord.com/oauth2/authorize?client_id={self.bot.user.id}&"
            "scope=bot+applications.commands&permissions=1099511627767"
        )

    @commands.command(name="custominfo")
    @commands.is_owner()
    async def custominfo(
        self, ctx: MartinContext, *, custom_info: Optional[str] = None
    ) -> None:
        """
        Add a custom info from the [p]info command.

        Leave blank to clear.
        """
        if custom_info is None:
            await self.db.get_or_delete_custom_info(True)
        elif await self.db.get_or_delete_custom_info(False):
            await self.db.insert_or_update_custom_info(True, custom_info)
        else:
            await self.db.insert_or_update_custom_info(False, custom_info)

        await ctx.send(content="Done.")
