from datetime import datetime, timezone
from time import perf_counter

import discord
from discord.ext import commands

from Martin import Martin, MartinContext
from Utilities.formatting import format_time


class General(commands.Cog):
    """
    General Cog.

    Various general commands for your needs.
    """

    def __init__(self, bot: Martin):
        self.bot = bot

    @staticmethod
    def _latency_colour(latency_ms: float) -> discord.Colour:
        if latency_ms < 100:
            return discord.Colour.green()
        if latency_ms < 250:
            return discord.Colour.yellow()
        return discord.Colour.red()

    @commands.command(name="uptime")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def uptime(self, ctx: MartinContext):
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
        )
        await ctx.send(embed=embed)

    @commands.command(name="ping")
    @commands.bot_has_permissions(embed_links=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ping(self, ctx: MartinContext):
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
            colour=self._latency_colour(heartbeat_latency),
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
            colour=self._latency_colour(heartbeat_latency),
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
