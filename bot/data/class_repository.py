from typing import Union

import aiosqlite
import discord

from bot.data.base_repository import BaseRepository
from bot.models.class_models import ClassSemester, ClassChannel, ClassTA


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

    async def search_class_narrow(self, prefix: str, num: int) -> list[ClassChannel]:
        """
        Searches for any registered class with the given class abbreviation and class number.
        """
        pass

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
        Checks against both the class_role_id and the class_ta_role_id.
        """
        role_id = role if isinstance(role, int) else role.id
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute('SELECT * FROM ClassChannel WHERE class_role_id = ? OR class_ta_role_id = ?',
                                      (role_id, role_id))
            dictionary = await self.fetch_first_as_dict(cursor)
            if not dictionary:
                return None
            return ClassChannel(**dictionary)

    async def insert_class(self, cls: ClassChannel) -> None:
        """
        Inserts the given ClassChannel model into the database.
        """
        async with aiosqlite.connect(self.resolved_db_path) as db:
            await db.execute("INSERT INTO ClassChannel VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                             (cls.channel_id, cls.semester_id, cls.category_id, cls.class_role_id, cls.class_prefix,
                              cls.class_number, cls.post_message_id, cls.class_professor, cls.class_name,
                              cls.class_archived, None))
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
        All members of the ClassChannel model are updated except the channel_id.
        """
        async with aiosqlite.connect(self.resolved_db_path) as db:
            await db.execute('UPDATE ClassChannel SET semester_id = ?, category_id = ?, class_role_id = ?, '
                             'class_prefix = ?, class_number = ?, post_message_id = ?, class_professor = ?, '
                             'class_name = ?, class_archived = ?, class_ta_role_id = ? '
                             'WHERE channel_id = ?',
                             (cls.semester_id, cls.category_id, cls.class_role_id,
                              cls.class_prefix, cls.class_number, cls.post_message_id, cls.class_professor,
                              cls.class_name, cls.class_archived, cls.class_ta_role_id, cls.channel_id))
            await db.commit()

    async def insert_ta(self, ta_model: ClassTA) -> None:
        """
        Inserts the given ClassTA model into the database.
        """
        async with aiosqlite.connect(self.resolved_db_path) as db:
            await db.execute('INSERT INTO ClassTA VALUES (?, ?, ?, ?)',
                             (ta_model.channel_id, ta_model.ta_user_id, ta_model.ta_display_tag, ta_model.ta_details))
            await db.commit()

    async def delete_ta(self, ta_model: ClassTA) -> None:
        """
        Deletes the ClassTA where the channel_id and ta_user_id are present.
        """
        async with aiosqlite.connect(self.resolved_db_path) as db:
            await db.execute('DELETE FROM ClassTA WHERE channel_id = ? AND ta_user_id = ?',
                             (ta_model.channel_id, ta_model.ta_user_id))
            await db.commit()

    async def update_ta(self, ta_model: ClassTA) -> None:
        """
        Updates the ClassTA where the channel_id and ta_user_id are present.
        Specifically, the following are updated:
        - ta_display_tag
        - ta_details
        """
        async with aiosqlite.connect(self.resolved_db_path) as db:
            await db.execute('UPDATE ClassTA SET ta_display_tag = ?, ta_details = ? '
                             'WHERE channel_id = ? AND ta_user_id = ?',
                             (ta_model.ta_display_tag, ta_model.ta_details, ta_model.channel_id, ta_model.ta_user_id))
            await db.commit()

    async def get_ta(self,
                     user: Union[int, discord.User, discord.Member],
                     channel: Union[int, discord.TextChannel]) -> ClassTA | None:
        """
        Searches for a ClassTA with the given user and channel.
        """
        user_id = user if isinstance(user, int) else user.id
        channel_id = channel if isinstance(channel, int) else channel.id
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute('SELECT * FROM ClassTA WHERE ta_user_id = ? AND channel_id = ?',
                                      (user_id, channel_id))
            dictionary = await self.fetch_first_as_dict(cursor)
            if not dictionary:
                return None
            return ClassTA(**dictionary)

    async def get_tas_by_channel(self, channel: Union[int, discord.TextChannel]) -> list[ClassTA]:
        """
        Searches for all ClassTA's for the given channel.
        """
        channel_id = channel if isinstance(channel, int) else channel.id
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute('SELECT * FROM ClassTA WHERE channel_id = ?', (channel_id,))
            return [ClassTA(**d) for d in await self.fetch_all_as_dict(cursor)]

    async def get_tas_by_user(self, user: Union[int, discord.User, discord.Member]) -> list[ClassTA]:
        """
        Searches for all ClassTA's for the given user.
        """
        user_id = user if isinstance(user, int) else user.id
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute('SELECT * FROM ClassTA WHERE ta_user_id = ?', (user_id,))
            return [ClassTA(**d) for d in await self.fetch_all_as_dict(cursor)]

    async def is_ta_role(self, role: Union[int, discord.Role]) -> bool:
        """
        Checks if the given role is registered as a TA role for a class channel.
        """
        role_id = role if isinstance(role, int) else role.id
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute('SELECT * FROM ClassChannel WHERE class_ta_role_id = ?', (role_id,))
            return len(await self.fetch_all_as_dict(cursor)) > 0
