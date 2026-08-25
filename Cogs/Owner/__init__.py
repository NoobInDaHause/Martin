from Martin import Martin

from .owner import Owner


async def setup(bot: Martin) -> None:
    await bot.add_cog(Owner(bot))
