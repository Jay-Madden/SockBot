import logging
from typing import Any

import aiosqlite

log = logging.getLogger(__name__)


class BaseRepository:
    """
    The base level repository that defines the fully resolved path for
    sqlite connection
    """

    def __init__(self):
        self.resolved_db_path = f'database/SockBot.db'

    async def fetch_all_as_dict(self, cursor: aiosqlite.Cursor) -> list[dict[Any, Any]]:
        """
        This function returns a list of dictionaries that contains the row names of the sql query
        as keys in a dictionary instead of the cursor result being index based which
        can be unclear and confusing

        Args:
            cursor (aiosqlite.Cursor): The cursor object that contains the query to be ran

        Returns:
            [list(dict)]: a list of dictionaries with row names as keys
        """
        return [dict(zip([column[0] for column in cursor.description], row))
                for row in await cursor.fetchall()]

    async def fetch_all_as_class(self, cursor: aiosqlite.Cursor):
        """
        This function returns a list of objects that contains the row names of the sql query
        as attributes in the object instead of the cursor result being index based which
        can be unclear and confusing

        Args:
            cursor (aiosqlite.Cursor): The cursor object that contains the query to be ran

        Returns:
            [cls]: a list of classes with row names as attributes
        """
        return [type('Query', (), dict(zip([column[0] for column in cursor.description], row)))
                for row in await cursor.fetchall()]

    async def fetch_first_as_dict(self, cursor: aiosqlite.Cursor) -> dict[Any, Any]:
        """
        This function returns a dictionary that contains the row names of the sql query
        as keys in a dictionary instead of the cursor result being index based which
        can be unclear and confusing

        Args:
            cursor (aiosqlite.Cursor): The cursor object that contains the query to be ran

        Returns:
            [dict]: a dictionary with row names as keys
        """
        if not (row := await cursor.fetchone()):
            return {}
        return dict(zip([column[0] for column in cursor.description], row))

    async def fetch_first_as_class(self, cursor: aiosqlite.Cursor):
        """
        This function returns a class that contains the row names of the sql query
        as attributes of the class instead of the cursor result being index based which
        can be unclear and confusing

        Args:
            cursor (aiosqlite.Cursor): The cursor object that contains the query to be ran

        Returns:
            [dict]: a class with row names as attributes
        """
        return type('Query', (), dict(zip([column[0] for column in cursor.description], await cursor.fetchone())))
