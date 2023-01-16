import datetime
from typing import Union

import aiosqlite
import discord

from bot.data.base_repository import BaseRepository
from bot.models.class_models import ClassSemester, ClassChannel

FORMAT = '%Y-%m-%d %H:%M:%S'


class ClassRepository(BaseRepository):

    async def get_all_semesters(self) -> list[ClassSemester]:
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute("SELECT * FROM ClassSemester")
            return [ClassSemester(**d) for d in await self.fetcthall_as_dict(cursor)]

    async def get_current_semester(self) -> ClassSemester | None:
        current_datetime = datetime.datetime.utcnow()
        # convert strings to datetimes and compare with current datetime
        for semester in await self.get_all_semesters():
            semester_start = strtodt(semester.semester_start)
            semester_end = strtodt(semester.semester_end)
            if semester_start <= current_datetime <= semester_end:
                return semester
        return None

    async def get_next_semester(self) -> ClassSemester | None:
        current_datetime = datetime.datetime.utcnow()
        for semester in await self.get_all_semesters():
            semester_start = strtodt(semester.semester_start)
            if current_datetime <= semester_start:
                return semester
        return None

    async def get_unarchived_classes(self) -> list[ClassChannel]:
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute("SELECT * FROM ClassChannel WHERE class_archived IS FALSE")
            return [ClassChannel(**d) for d in await self.fetcthall_as_dict(cursor)]

    async def get_semester_classes(self, semester: ClassSemester, unarchived_only: bool = True) -> list[ClassChannel]:
        statement = 'SELECT * FROM ClassChannel WHERE semester_id = ?' \
                    + ' AND class_archived IS FALSE' if unarchived_only else ''
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute(statement, (semester.semester_id,))
            return [ClassChannel(**d) for d in await self.fetcthall_as_dict(cursor)]

    async def search_semester(self, semester_id: str) -> ClassSemester | None:
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute("SELECT * FROM ClassSemester WHERE semester_id = ?", (semester_id,))
            dictionary = await self.fetcthall_as_dict(cursor)
            if not len(dictionary):
                return None
            return ClassSemester(**dictionary)

    async def search_class(self, prefix: str, num: int, prof: str) -> ClassChannel | None:
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute(
                """ SELECT * FROM ClassChannel 
                    WHERE class_prefix = ? 
                    AND class_number = ? 
                    AND class_professor = ?""", (prefix, num, prof)
            )
            dictionary = await self.fetcthone_as_dict(cursor)
            if not len(dictionary):
                return None
            return ClassChannel(**dictionary)

    async def search_class_by_channel(self, channel: Union[discord.TextChannel, int]) -> ClassChannel | None:
        channel_id = channel if isinstance(channel, int) else channel.id
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute('SELECT * FROM ClassChannel WHERE channel_id = ?', (channel_id,))
            dictionary = await self.fetcthone_as_dict(cursor)
            if not len(dictionary):
                return None
            return ClassChannel(**dictionary)

    async def insert_class(self, cls: ClassChannel) -> None:
        async with aiosqlite.connect(self.resolved_db_path) as db:
            await db.execute("INSERT INTO ClassChannel VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                             (cls.channel_id, cls.semester_id, cls.category_id,
                              cls.class_role_id, cls.class_prefix, cls.class_number,
                              cls.post_message_id, cls.class_professor, cls.class_name))
            await db.commit()


def strtodt(date: str) -> datetime.datetime:
    """A simple util for translating UTC timestamps in the database to UTC datetime.datetime objects."""
    return datetime.datetime.strptime(date, FORMAT)
