from Martin import Martin

from .moderation import Moderation


async def setup(bot: Martin):
    await bot.add_cog(Moderation(bot))
