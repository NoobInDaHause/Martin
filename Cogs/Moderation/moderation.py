import discord

from discord.ext import commands
from discord import app_commands

from Martin import Martin, MartinInteraction


class Moderation(commands.GroupCog, group_name="moderation"):
    def __init__(self, bot: Martin):
        super().__init__()
        self.bot = bot

    @app_commands.command(name="kick", description="Kick a member.")
    @app_commands.checks.bot_has_permissions(kick_members=True)
    @app_commands.checks.has_permissions(kick_members=True)
    async def moderation_kick(
        self, interaciton: MartinInteraction, member: discord.Member, reason: str = None
    ):
        await interaciton.guild.kick(member, reason=reason or "No reason given.")
