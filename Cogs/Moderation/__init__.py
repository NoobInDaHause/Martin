from .moderation import Moderation

from Martin import Martin


async def setup(bot: Martin):
    await bot.add_cog(Moderation(bot))
