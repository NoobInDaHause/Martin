from typing import Any, Literal, Optional

import aiosqlite

from Martin.settings import COGS_DATA_PATH
from Utilities.exceptions import DataManagerException
from Utilities.formatting import format_list


class DataManager:
    """Manages database operations for cogs.\n
    \n    This class handles SQLite database connections and executes SQL commands\n    for storing and retrieving cog-specific data.
    """

    def __init__(self, cog_name: str) -> None:
        """Initialize the DataManager instance.

        Parameters
        ----------
        cog_name : str
            The name of the cog for which the database is created.
        """
        self.path = COGS_DATA_PATH / f"{cog_name}.db"

    async def execute(
        self,
        sql_command: str,
        args: tuple = None,
        select: bool = False,
        one_all: Literal["one", "all"] = "one",
    ) -> Optional[Any]:
        """Execute a SQL command.

        Parameters
        ----------
        sql_command : str
            The SQL command to execute.
        args : tuple, optional
            Arguments to pass to the SQL command. Defaults to None.
        select : bool, optional
            Whether this is a SELECT query. Defaults to False.
        one_all : Literal["one", "all"], optional
            Whether to return one result or all results. Defaults to "one".

        Returns
        -------
        Optional[Any]
            The query result for SELECT queries, None otherwise.

        Raises
        ------
        DataManagerException
            If one_all is not "one" or "all" when select is True.
        """
        accepted = {"one", "all"}
        if select and one_all not in accepted:
            raise DataManagerException(
                f"Parameter 'one_all_many' should only be {format_list(list(accepted))}."
            )

        async with aiosqlite.connect(self.path) as db:
            if args is not None:
                cursor = await db.execute(sql_command, args)
            else:
                cursor = await db.execute(sql_command)

            if select:
                return (
                    await cursor.fetchone()
                    if one_all == "one"
                    else await cursor.fetchall()
                )

            await db.commit()
