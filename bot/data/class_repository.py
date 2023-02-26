from typing import Union

import aiosqlite
import discord

from bot.data.base_repository import BaseRepository
from bot.models.class_models import ClassSemester, ClassChannel


class ClassRepository(BaseRepository):

    async def get_all_semesters(self) -> list[ClassSemester]:
        """
        Fetches all semesters from the database.
        """
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute("SELECT * FROM ClassSemester")
            return [ClassSemester(**d) for d in await self.fetch_all_as_dict(cursor)]

    async def get_current_semester(self) -> ClassSemester | None:
        """
        Gets the current semester, if one exists.
        """
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute("""SELECT * FROM ClassSemester 
                                         WHERE semester_start <= strftime('%Y-%m-%d %H:%M:%S', datetime('now')) 
                                         AND strftime('%Y-%m-%d %H:%M:%S', datetime('now')) <= semester_end""")
            dictionary = await self.fetch_first_as_dict(cursor)
            if not dictionary:
                return None
            return ClassSemester(**dictionary)

    async def get_next_semester(self) -> ClassSemester | None:
        """
        Gets the next semester, if one exists.
        """
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute("""SELECT * FROM ClassSemester
                                         WHERE semester_start > strftime('%Y-%m-%d %H:%M:%S', datetime('now'))""")
            dictionary = await self.fetch_first_as_dict(cursor)
            if not dictionary:
                return None
            return ClassSemester(**dictionary)

    async def get_unarchived_classes(self) -> list[ClassChannel]:
        """
        Gets a list of class channels that are currently marked as unarchived.
        """
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute("SELECT * FROM ClassChannel WHERE class_archived IS FALSE")
            return [ClassChannel(**d) for d in await self.fetch_all_as_dict(cursor)]

    async def get_semester_classes(self, semester: ClassSemester) -> list[ClassChannel]:
        """
        Gets a list of class channels for a specific semester, with the ability to
        only fetch the ones that are currently marked as unarchived.
        """
        statement = 'SELECT * FROM ClassChannel WHERE semester_id = ?'
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute(statement, (semester.semester_id,))
            return [ClassChannel(**d) for d in await self.fetch_all_as_dict(cursor)]

    async def search_semester(self, semester_id: str) -> ClassSemester | None:
        """
        Searches for a semester with the given semester ID.
        Note that this does not search for the semester name, which is different.
        ex: Semester Name: Spring 2023, Semester ID: sp2023
        """
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute("SELECT * FROM ClassSemester WHERE semester_id = ?", (semester_id,))
            dictionary = await self.fetch_first_as_dict(cursor)
            if not dictionary:
                return None
            return ClassSemester(**dictionary)

    async def search_class(self, prefix: str, num: int, prof: str) -> ClassChannel | None:
        """
        Searches for a registered class given the class abbreviation, class number, and class instructor.
        """
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute(
                """ SELECT * FROM ClassChannel 
                    WHERE class_prefix = ? 
                    AND class_number = ? 
                    AND class_professor = ?""", (prefix, num, prof)
            )
            dictionary = await self.fetch_first_as_dict(cursor)
            if not dictionary:
                return None
            return ClassChannel(**dictionary)

    async def search_class_by_channel(self, channel: Union[discord.TextChannel, int]) -> ClassChannel | None:
        """
        Searches for a registered class with the given channel ID or channel itself.
        """
        channel_id = channel if isinstance(channel, int) else channel.id
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute('SELECT * FROM ClassChannel WHERE channel_id = ?', (channel_id,))
            dictionary = await self.fetch_first_as_dict(cursor)
            if not dictionary:
                return None
            return ClassChannel(**dictionary)

    async def search_class_by_role(self, role: Union[discord.Role, int]) -> ClassChannel | None:
        """
        Searches for a registered class with the given role ID or role itself.
        """
        role_id = role if isinstance(role, int) else role.id
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute('SELECT * FROM ClassChannel WHERE class_role_id = ?', (role_id,))
            dictionary = await self.fetch_first_as_dict(cursor)
            if not dictionary:
                return None
            return ClassChannel(**dictionary)

    async def insert_class(self, cls: ClassChannel) -> None:
        """
        Inserts the given ClassChannel model into the database.
        class_archived from the model is not inserted and is instead defaulted to False.
        """
        async with aiosqlite.connect(self.resolved_db_path) as db:
            await db.execute("INSERT INTO ClassChannel VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, FALSE)",
                             (cls.channel_id, cls.semester_id, cls.category_id,
                              cls.class_role_id, cls.class_prefix, cls.class_number,
                              cls.post_message_id, cls.class_professor, cls.class_name))
            await db.commit()

    async def delete_class(self, channel: Union[int, ClassChannel]) -> None:
        """
        Deletes the ClassChannel with the given channel or channel id.
        """
        channel_id = channel if isinstance(channel, int) else channel.channel_id
        async with aiosqlite.connect(self.resolved_db_path) as db:
            await db.execute('DELETE FROM ClassChannel WHERE channel_id = ?', (channel_id,))
            await db.commit()

    async def update_class(self, cls: ClassChannel) -> None:
        """
        Updates the ClassChannel object in the database.
        Specifically, the following are updated:
        - semester_id
        - category_id
        - class_role_id
        - post_message_id
        - class_archived
        """
        async with aiosqlite.connect(self.resolved_db_path) as db:
            await db.execute('UPDATE ClassChannel SET semester_id = ?, category_id = ?,'
                             'class_role_id = ?, post_message_id = ?, class_archived = ? '
                             'WHERE channel_id = ?',
                             (cls.semester_id, cls.category_id, cls.class_role_id,
                              cls.post_message_id, cls.class_archived, cls.channel_id))
            await db.commit()
