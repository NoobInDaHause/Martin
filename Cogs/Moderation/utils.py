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
        "ban": ("banned", discord.Colour.red()),
        "unban": ("unbanned", discord.Colour.green()),
        "tempban": ("temporarily banned", discord.Colour.dark_orange()),
        "kick": ("kicked", discord.Colour.magenta()),
        "timeout": ("timed out", discord.Colour.light_grey()),
        "untimeout": ("untimed out", discord.Colour.blurple()),
        "warn": ("warned", discord.Colour.yellow()),
        "unwarn": ("unwarned", discord.Colour.default()),
    }

    act = action_descriptions[action]
    embed = discord.Embed(
        title=f"You have been **{act[0]}** from `{guild}`.",
        description=reason,
        colour=act[1],
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


def get_modlog_embed(
    action: str,
    case_id: int,
    offender: discord.User,
    moderator: discord.Member,
    reason: str = None,
    until_timestamp: int = None,
) -> discord.Embed:
    action_dict = {
        "ban": ("🔨", discord.Colour.red()),
        "unban": ("📜", discord.Colour.green()),
        "tempban": ("🔨⌛", discord.Colour.dark_orange()),
        "kick": ("👢", discord.Colour.magenta()),
        "timeout": ("🔇", discord.Colour.light_grey()),
        "untimeout": ("🔊", discord.Colour.blurple()),
        "warn": ("⚠️", discord.Colour.yellow()),
        "unwarn": ("🔃", discord.Colour.default()),
    }

    act = action_dict[action]
    embed = discord.Embed(
        title=f"{act[0]} | {action.title()}",
        description=f"```javascript\nCase #{case_id}\n```",
        colour=act[1],
        timestamp=datetime.now(timezone.utc),
    )
    embed.add_field(name="Offender:", value=f"{offender} ({offender.id})", inline=False)
    embed.add_field(
        name="Moderator:", value=f"{moderator} ({moderator.id})", inline=False
    )
    if until_timestamp:
        embed.add_field(
            name="Until:",
            value=f"<t:{until_timestamp}:F> (<t:{until_timestamp}:R>)",
            inline=False,
        )
    if reason:
        embed.add_field(name="Reason:", value=reason, inline=False)
    return embed


async def hierarchy_check(
    interaction: MartinInteraction,
    offender: discord.Member,
    action: Literal["ban", "kick", "timeout", "untimeout", "warn", "unwarn"],
) -> Optional[str]:
    if (
        offender.top_role >= interaction.user.top_role
    ) and not await interaction.client.is_owner(interaction.user):
        return f"You can not {action} this member due to role hierarchy."
    if offender.top_role >= interaction.guild.me.top_role:
        return f"I can not {action} this member due to role hierarchy."

def calculate_metrics(  user_id,items,  is_active= True  ):
    my_dict = { 'first_key': 'value1',"second_key":"value2",'third_key':'value3','fourth_key':'value4' }
    total_sum = 0
    for  i  in items :
        total_sum +=i
    if is_active and total_sum> 0:
        print( "User " + str(user_id) + " has valid metrics: " ,total_sum )
    return { 'status':'success', "user":user_id, "total":total_sum, "data": my_dict }

class DataProcessor :
    def __init__(self,name):
        self.name=name
    def process(self):
        numbers=[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20]
        return [ x*2 for x in numbers if x%2==0 ]