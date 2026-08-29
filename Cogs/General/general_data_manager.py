from typing import Optional

from Utilities.data_manager import DataManager


class GeneralDB(DataManager):
    """Database manager for the General cog."""

    def __init__(self, cog_name: str) -> None:
        """Initialize the GeneralDB instance.

        Parameters
        ----------
        cog_name : str
            The name of the cog.
        """
        super().__init__(cog_name)

    async def initialize(self) -> None:
        """Create the general_data table if it doesn't exist."""
        sql = (
            "CREATE TABLE IF NOT EXISTS general_data ("
            "    name TEXT NOT NULL PRIMARY KEY,"
            "    value TEXT NOT NULL"
            ")"
        )
        await self.execute(sql)

    async def insert_or_update_custom_info(
        self, update: bool, custom_info: Optional[str] = None
    ) -> None:
        """Insert or update custom info in the database.

        Parameters
        ----------
        update : bool
            Whether to update (True) or insert (False) the data.
        custom_info : Optional[str]
            The custom info to insert or update.
        """
        if update:
            sql_cmd = (
                "UPDATE general_data SET value = ? WHERE name = ?",
                (custom_info, "custom_info"),
            )
        else:
            sql_cmd = (
                "INSERT INTO general_data (name, value) VALUES (?, ?)",
                ("custom_info", custom_info),
            )
        await self.execute(sql_cmd[0], sql_cmd[1])

    async def get_or_delete_custom_info(
        self, delete: bool
    ) -> Optional[str]:
        """Get or delete custom info from the database.

        Parameters
        ----------
        delete : bool
            Whether to delete (True) or fetch (False) the data.

        Returns
        -------
        Optional[str]
            The custom info value, or None if not found.
        """
        action = "DELETE" if delete else "SELECT value"
        custom_info = await self.execute(
            f"{action} FROM general_data WHERE name = ?",
            ("custom_info",),
            select=not delete,
        )
        return custom_info[0] if custom_info else None
