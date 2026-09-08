from typing import Literal
from datetime import datetime, timezone

import discord


def get_auditlog_reason(moderator: discord.Member, reason: str = None) -> str:
    audit_reason = f"Authoried by {moderator} ({moderator.id})."
    if reason:
        audit_reason += f" Reason: {reason}"
    return f"{audit_reason[:509]}..." if len(audit_reason) > 512 else audit_reason


def get_dm_embed(
    moderator: discord.Member,
    guild: discord.Guild,
    reason: str,
    action: Literal["ban", "unban", "tempban", "kick", "timeout", "untimeout"],
    until: datetime = None,
):
    title = f"You have been **[what]** from `{guild}`."
    embed = discord.Embed(
        title=title.replace(
            "[what]",
            (
                "banned"
                if action == "ban"
                else (
                    "unbanned"
                    if action == "unban"
                    else (
                        "temporarily banned"
                        if action == "tempban"
                        else (
                            "kicked"
                            if action == "kick"
                            else "timed out" if action == "timeout" else "untimed out"
                        )
                    )
                )
            ),
        ),
        description=reason,
        colour=moderator.colour,
        timestamp=datetime.now(timezone.utc),
    )
    embed.set_thumbnail(url=guild.icon)
    if until:
        embed.add_field(
            name="Until:",
            value=f"<t:{int(until.timestamp())}:F> (<t:{int(until.timestamp())}:R>)",
            inline=False,
        )
    embed.add_field(name="Moderator:", value=f"{moderator} ({moderator.id})", inline=False)

    return embed
