from typing import Optional

from Utilities.data_manager import DataManager


class ModerationDataBase(DataManager):
    def __init__(self, cog_name):
        super().__init__(cog_name)

    async def initialize(self) -> None:
        sql = (
            "CREATE TABLE IF NOT EXISTS tempbans ("
            "    guild_id INTEGER NOT NULL PRIMARY KEY,"
            "    offender_id INTEGER NOT NULL,"
            "    banned_until_timestamp INTEGER NOT NULL"
            ")"
        )
        await self.execute(sql)

    async def insert_tempban(
        self, guild_id: int, offender_id: int, banned_until_timestamp: int
    ) -> None:
        await self.execute(
            "INSERT INTO tempbans (guild_id, offender_id, banned_until_timestamp) VALUES (?, ?, ?)",
            (guild_id, offender_id, banned_until_timestamp),
        )

    async def get_or_delete_tempban(
        self, delete: bool, guild_id: int = None, offender_id: int = None
    ) -> Optional[int]:
        if delete:
            await self.execute(
                "DELETE FROM tempbans WHERE guild_id = ? AND offender_id = ?",
                (guild_id, offender_id),
            )
        else:
            custom_info = await self.execute(
                "SELECT banned_until_timestamp FROM tempbans WHERE guild_id = ? AND offender_id = ?",
                (guild_id, offender_id),
                select=True,
            )
            return custom_info[0]

    async def get_all_tempbans(self) -> tuple:
        return await self.execute("SELECT * FROM tempbans", select=True, one_all="all")
