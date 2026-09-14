from datetime import datetime, timezone
import discord


class TempbanObject:
    def __init__(self, **kwargs):
        self.offender: discord.User = kwargs.get("offender")
        self.moderator: discord.User = kwargs.get("moderator")
        self.guild: discord.Guild = kwargs.get("guild")
        self.until = datetime.fromtimestamp(kwargs.get("timestamp"), tz=timezone.utc)
