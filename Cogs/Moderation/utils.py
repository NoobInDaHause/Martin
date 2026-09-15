from __future__ import annotations

from typing import TYPE_CHECKING, Literal, Optional
from datetime import datetime, timezone

import discord

if TYPE_CHECKING:
    from Martin import MartinInteraction


def get_auditlog_reason(moderator: discord.Member, reason: str = None) -> str:
    audit_reason = f"Authorized by {moderator} ({moderator.id})."
    if reason:
        audit_reason += f" Reason: {reason}"
    return f"{audit_reason[:509]}..." if len(audit_reason) > 512 else audit_reason


def get_dm_embed(
    moderator: discord.Member,
    guild: discord.Guild,
    reason: str,
    action: Literal[
        "ban",
        "unban",
        "tempban",
        "kick",
        "timeout",
        "untimeout",
        "warn",
        "unwarn",
    ],
    until: Optional[datetime] = None,
) -> discord.Embed:
    action_descriptions = {
        "ban": "banned",
        "unban": "unbanned",
        "tempban": "temporarily banned",
        "kick": "kicked",
        "timeout": "timed out",
        "untimeout": "untimed out",
        "warn": "warned",
        "unwarn": "unwarned",
    }

    embed = discord.Embed(
        title=f"You have been **{action_descriptions[action]}** from `{guild}`.",
        description=reason,
        colour=moderator.colour,
        timestamp=datetime.now(timezone.utc),
    )

    embed.set_thumbnail(url=guild.icon)

    if until is not None:
        timestamp = int(until.timestamp())
        embed.add_field(
            name="Until:",
            value=f"<t:{timestamp}:F> (<t:{timestamp}:R>)",
            inline=False,
        )

    embed.add_field(
        name="Moderator:",
        value=f"{moderator} ({moderator.id})",
        inline=False,
    )

    return embed


async def hierarchy_check(
    interaction: MartinInteraction,
    offender: discord.Member,
    action: Literal["ban", "kick", "timeout", "untimeout"],
) -> Optional[str]:
    if (
        offender.top_role >= interaction.user.top_role
    ) and not await interaction.client.is_owner(interaction.user):
        return f"You can not {action} this member due to role hierarchy."
    if offender.top_role >= interaction.guild.me.top_role:
        return f"I can not {action} this member due to role hierarchy."
