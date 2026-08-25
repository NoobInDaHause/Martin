from Martin import Martin

from .general import General


async def setup(bot: Martin) -> None:
    await bot.add_cog(General(bot))
