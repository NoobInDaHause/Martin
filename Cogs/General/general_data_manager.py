import aiosqlite

from Martin.settings import COGS_DATA_PATH


class GeneralData:
    def __init__(self, cog_name: str):
        self.cog_name = cog_name
        self.path = COGS_DATA_PATH / f"{cog_name}.db"

    async def create_table(self):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.cog_name} (
                    name TEXT NOT NULL,
                    value TEXT NOT NULL
                )
            """)
            await db.commit()

    async def initialize(self):
        if not self.path.exists():
            await self.create_table()

    async def get_custom_info(self):
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                f"""SELECT value FROM {self.cog_name} WHERE name = ?""",
                ("custom_info",),
            )
            row = await cursor.fetchone()
            return row[0] if row else row

    async def update_custom_info(self, new_custom_info: str):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                f"""UPDATE {self.cog_name} SET value = ? WHERE name = ?""",
                (new_custom_info, "custom_info"),
            )
            await db.commit()

    async def insert_custom_info(self, custom_info: str):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                f"""INSERT INTO {self.cog_name} (name, value) VALUES (?, ?)""",
                ("custom_info", custom_info),
            )
            await db.commit()

    async def delete_custom_info(self):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                f"""DELETE FROM {self.cog_name} WHERE name = ?""", ("custom_info",)
            )
            await db.commit()
