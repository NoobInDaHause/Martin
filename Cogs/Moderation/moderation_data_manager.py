from typing import List, Optional

from Utilities.data_manager import DataManager


class ModerationDataBase(DataManager):
    def __init__(self, cog_name):
        super().__init__(cog_name)

    async def initialize_guild(self, guild_id: int) -> None:
        sql = (
            f"CREATE TABLE IF NOT EXISTS tempbans_{guild_id} ("
            "    offender_id INTEGER NOT NULL,"
            "    banned_until_timestamp INTEGER NOT NULL,"
            "    moderator_id INTEGER NOT NULL"
            ")"
        )
        await self.execute(sql)

    async def insert_tempban(
        self, guild_id: int, offender_id: int, banned_until_timestamp: int, moderator_id: int
    ) -> None:
        await self.initialize_guild(guild_id)
        await self.execute(
            f"INSERT INTO tempbans_{guild_id} (offender_id, banned_until_timestamp, moderator_id) VALUES (?, ?, ?)",
            (offender_id, banned_until_timestamp, moderator_id),
        )

    async def get_or_delete_tempban(
        self, delete: bool, guild_id: int = None, offender_id: int = None
    ) -> Optional[int]:
        if delete:
            await self.execute(
                f"DELETE FROM tempbans_{guild_id} WHERE offender_id = ?",
                (offender_id,),
            )
        else:
            tban = await self.execute(
                f"SELECT * FROM tempbans_{guild_id} WHERE offender_id = ?",
                (offender_id,),
                select=True,
            )
            return tban[0]

    async def get_all_tempbans_from_guild(self, guild_id: int) -> List[tuple]:
        return await self.execute(
            f"SELECT * FROM tempbans_{guild_id}", select=True, one_all="all"
        )

    async def get_all_tempbans(self) -> tuple:
        all_guilds = await self.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            AND name NOT LIKE 'sqlite_%'
            """,
            select=True,
            one_all="all",
        )

        data = []

        for guild_id in all_guilds:
            guild_id = int(guild_id[0].removeprefix("tempbans_"))
            if all_tempbans := await self.get_all_tempbans_from_guild(guild_id):
                data.extend([(guild_id, o_id, bui, m_id) for o_id, bui, m_id in all_tempbans])
        return data
