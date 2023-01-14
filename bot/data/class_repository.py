import dataclasses
import datetime
from pyclbr import Class
from typing import TypeVar, Any

import aiosqlite

from bot.data.base_repository import BaseRepository
from bot.models.class_models import ClassSemester, ClassChannel

FORMAT = '%Y-%m-%d %H:%M:%S'
T = TypeVar("T", bound=dataclasses.dataclass)


class ClassRepository(BaseRepository):

    async def get_current_semester(self) -> ClassSemester | None:
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute("SELECT * FROM ClassSemester")
            semesters: list[ClassSemester] = await self.fetcthall_as_class(cursor)
            current_datetime = datetime.datetime.utcnow()
            # convert strings to datetimes and compare with current datetime
            for semester in semesters:
                semester_start = strtodt(semester.semester_start)
                semester_end = strtodt(semester.semester_end)
                if semester_start <= current_datetime <= semester_end:
                    return semester
            return None

    async def get_unarchived_classes(self) -> list[ClassChannel]:
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute("SELECT * FROM ClassChannel WHERE class_archived IS FALSE")
            return await self.fetcthall_as_class(cursor)

    async def get_semester_classes(self, semester: ClassSemester, unarchived_only: bool = True) -> list[ClassChannel]:
        statement = 'SELECT * FROM ClassChannel WHERE semester_id = ?' \
                    + ' AND class_archived IS FALSE' if unarchived_only else ''
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute(statement, (semester.semester_id,))
            return await self.fetcthall_as_class(cursor)

    async def search_semester(self, semester_id: str) -> ClassSemester | None:
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute("SELECT * FROM ClassSemester WHERE semester_id = ?", (semester_id,))
            return await self.fetcthone_as_class(cursor)

    async def search_class(self, prefix: str, num: int, prof: str) -> ClassChannel | None:
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute(
                """ SELECT * FROM ClassChannel 
                    WHERE class_prefix = ? 
                    AND class_number = ? 
                    AND class_professor = ?""", (prefix, num, prof))
            return await self.fetcthone_as_class(cursor)

    async def insert_class(self, clazz: ClassChannel) -> None:
        semester = await self.get_current_semester()
        assert semester is not None
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute("""INSERT INTO ClassChannel WITH VALUES (?, ?, ?, ?)
            """)
        pass


def strtodt(date: str) -> datetime.datetime:
    """A simple util for translating UTC timestamps in the database to UTC datetime.datetime objects."""
    return datetime.datetime.strptime(date, FORMAT)
