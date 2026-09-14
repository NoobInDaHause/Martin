from typing import List, Optional

from Utilities.data_manager import DataManager


class ModerationDataBase(DataManager):
    def __init__(self, cog_name: str):
        super().__init__(cog_name)

    async def initialize(self) -> None:
        """Create the shared tempban table if it does not exist."""
        await self.execute("""
            CREATE TABLE IF NOT EXISTS tempbans (
                guild_id INTEGER NOT NULL,
                offender_id INTEGER NOT NULL,
                banned_until_timestamp INTEGER NOT NULL,
                moderator_id INTEGER,
                PRIMARY KEY (guild_id, offender_id)
            )
            """)

    async def insert_tempban(
        self,
        guild_id: int,
        offender_id: int,
        banned_until_timestamp: int,
        moderator_id: int,
    ) -> None:
        await self.initialize()
        await self.execute(
            """
            INSERT INTO tempbans
                (guild_id, offender_id, banned_until_timestamp, moderator_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT (guild_id, offender_id) DO UPDATE SET
                banned_until_timestamp = excluded.banned_until_timestamp,
                moderator_id = excluded.moderator_id
            """,
            (guild_id, offender_id, banned_until_timestamp, moderator_id),
        )

    async def get_tempban(self, guild_id: int, offender_id: int) -> Optional[tuple]:
        await self.initialize()
        return await self.execute(
            """
            SELECT banned_until_timestamp, moderator_id
            FROM tempbans
            WHERE guild_id = ? AND offender_id = ?
            """,
            (guild_id, offender_id),
            select=True,
        )

    async def delete_tempban(self, guild_id: int, offender_id: int) -> None:
        await self.initialize()
        await self.execute(
            "DELETE FROM tempbans WHERE guild_id = ? AND offender_id = ?",
            (guild_id, offender_id),
        )

    async def get_all_tempbans_from_guild(self, guild_id: int) -> List[tuple]:
        await self.initialize()
        return await self.execute(
            """
            SELECT offender_id, banned_until_timestamp, moderator_id
            FROM tempbans
            WHERE guild_id = ?
            ORDER BY offender_id
            """,
            (guild_id,),
            select=True,
            one_all="all",
        )

    async def get_all_tempbans(self) -> List[tuple]:
        await self.initialize()
        return await self.execute(
            """
            SELECT guild_id, offender_id, banned_until_timestamp, moderator_id
            FROM tempbans
            ORDER BY guild_id, offender_id
            """,
            select=True,
            one_all="all",
        )
