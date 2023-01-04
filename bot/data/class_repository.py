import datetime

import aiosqlite

from bot.data.base_repository import BaseRepository
from bot.models.class_models import ClassSemester

FORMAT = '%Y-%m-%d %H:%M:%S'


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


def strtodt(date: str) -> datetime.datetime:
    """A simple util for translating UTC timestamps in the database to UTC datetime.datetime objects."""
    return datetime.datetime.strptime(date, FORMAT)
