from typing import List, Optional

from Utilities.data_manager import DataManager


class ModerationDataBase(DataManager):
    def __init__(self, cog_name: str):
        super().__init__(cog_name)

    # -------------------------------------------- tempbans -------------------------------------------------------
    async def initialize_tempbans(self) -> None:
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
        await self.execute(
            """
            INSERT INTO tempbans
                (guild_id, offender_id, banned_until_timestamp, moderator_id)
            VALUES (?, ?, ?, ?)
            """,
            (guild_id, offender_id, banned_until_timestamp, moderator_id),
        )

    async def get_tempban(self, guild_id: int, offender_id: int) -> Optional[tuple]:
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
        await self.execute(
            "DELETE FROM tempbans WHERE guild_id = ? AND offender_id = ?",
            (guild_id, offender_id),
        )

    async def get_all_tempbans_from_guild(self, guild_id: int) -> List[tuple]:
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

    # reserved in the future
    async def get_all_tempbans(self) -> List[tuple]:
        return await self.execute(
            """
            SELECT guild_id, offender_id, banned_until_timestamp, moderator_id
            FROM tempbans
            ORDER BY guild_id, offender_id
            """,
            select=True,
            one_all="all",
        )

    # -------------------------------------------- warnings -------------------------------------
    async def initialize_warnings(self):
        await self.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                guild_id INTEGER NOT NULL,
                warn_id INTEGER NOT NULL,
                offender_id INTEGER NOT NULL,
                moderator_id INTEGER,
                reason TEXT,
                PRIMARY KEY (guild_id, warn_id)
            )
            """)

    async def insert_warning(
        self,
        guild_id: int,
        offender_id: int,
        moderator_id: int,
        reason: str = None,
    ) -> None:
        await self.execute(
            """
            INSERT INTO warnings
                (guild_id, warn_id, offender_id, moderator_id, reason)
            VALUES (
                ?,
                (SELECT COALESCE(MAX(warn_id), 0) + 1 FROM warnings WHERE guild_id = ?),
                ?,
                ?,
                ?
            )
            """,
            (guild_id, guild_id, offender_id, moderator_id, reason),
        )

    async def get_warning(self, guild_id: int, warn_id: int) -> List[tuple]:
        return await self.execute(
            "SELECT * FROM warnings WHERE guild_id = ? AND warn_id = ?",
            (guild_id, warn_id),
            select=True,
            one_all="all",
        )

    async def delete_warning(self, guild_id: int, warn_id: int) -> None:
        await self.execute(
            "DELETE FROM warnings WHERE guild_id = ? AND warn_id = ?",
            (guild_id, warn_id),
        )

    async def get_all_warnings_from_guild(self, guild_id: int) -> List[tuple]:
        return await self.execute(
            "SELECT * FROM warnings WHERE guild_id = ?",
            (guild_id,),
            select=True,
            one_all="all",
        )

    async def get_all_warnings_from_offender(self, guild_id: int, offender_id: int) -> List[tuple]:
        return await self.execute(
            "SELECT * FROM warnings WHERE guild_id = ? AND offender_id = ?",
            (guild_id, offender_id),
            select=True,
            one_all="all",
        )

    # reserved for the future
    async def get_all_warnings(self) -> List[tuple]:
        return await self.execute(
            """
            SELECT * FROM warnings
            ORDER BY guild_id, warn_id
            """,
            select=True,
            one_all="all",
        )
