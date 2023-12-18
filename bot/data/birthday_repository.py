from datetime import datetime
from typing import Optional, List

import aiosqlite

from bot.data.base_repository import BaseRepository
from bot.models.birthday_model import Birthday


class BirthdayRepository(BaseRepository):

    async def get_birthday(self, member_id: int) -> Optional[Birthday]:
        try:
            async with aiosqlite.connect(self.resolved_db_path) as db:
                return await self.fetch_first_as_class(
                    await db.execute("SELECT * FROM Birthdays WHERE member_id = ?", (member_id,)))
        except TypeError:
            return

    async def add_birthday(self, member_id: int, month: int, day: int, year: Optional[int] = None) -> None:
        async with aiosqlite.connect(self.resolved_db_path) as db:
            await db.execute("INSERT INTO Birthdays(member_id, month, day, year, last_used) VALUES (?, ?, ?, ?, ?)",
                             (member_id, month, day, year, datetime.now()))
            await db.commit()

    async def update_birthday(self, member_id: int, month: int, day: int, year: Optional[int] = None) -> None:
        async with aiosqlite.connect(self.resolved_db_path) as db:
            await db.execute("UPDATE Birthdays SET month = ?, day = ?, year = ?, last_used = ? WHERE member_id = ?",
                             (month, day, year, datetime.now(), member_id))
            await db.commit()

    async def update_last_congratulated(self, member_id: int) -> None:
        async with aiosqlite.connect(self.resolved_db_path) as db:
            await db.execute("UPDATE Birthdays SET last_congratulated = ? WHERE member_id = ?",
                             (datetime.now(), member_id))
            await db.commit()

    async def get_todays_birthdays(self) -> List[Birthday]:
        try:
            async with aiosqlite.connect(self.resolved_db_path) as db:
                today = datetime.now()
                cursor = await db.execute("SELECT * FROM Birthdays WHERE month = ? AND day = ?",
                                          (today.month, today.day))
                return await self.fetch_all_as_class(cursor)
        except TypeError:
            return []

    async def get_non_birthdays(self) -> List[Birthday]:
        try:
            async with aiosqlite.connect(self.resolved_db_path) as db:
                today = datetime.now()
                cursor = await db.execute("SELECT * FROM Birthdays WHERE month != ? OR day != ?",
                                          (today.month, today.day))
                return await self.fetch_all_as_class(cursor)
        except TypeError:
            return []
