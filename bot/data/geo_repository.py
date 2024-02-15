import aiosqlite
from bot.data.base_repository import BaseRepository
from bot.models.geo_models import GeoguessrLeaderboard


class GeoRepository(BaseRepository):

    async def get_rank(self) -> list[dict]:
        async with aiosqlite.connect(self.resolved_db_path) as connection:
            cursor = await connection.execute('SELECT *, ROW_NUMBER() OVER(ORDER BY score DESC) AS RANK from '
                                              'GeoguessrLeaderboard')
            return await self.fetch_all_as_dict(cursor)

    async def return_size(self) -> int:
        async with aiosqlite.connect(self.resolved_db_path) as connection:
            cursor = await connection.execute('SELECT COUNT(*) FROM GeoguessrLeaderboard;')
            return int((await self.fetch_first_as_dict(cursor))['COUNT(*)'])

    async def update_score(self, score, user_id):
        async with aiosqlite.connect(self.resolved_db_path) as connection:
            await connection.execute('UPDATE GeoguessrLeaderboard SET score = ? WHERE user_id = ?;', (score, user_id,))
            await connection.commit()

    async def sort_and_return(self) -> list[dict]:
        async with aiosqlite.connect(self.resolved_db_path) as connection:
            cursor = await connection.execute('SELECT * FROM GeoguessrLeaderboard ORDER BY score DESC LIMIT 10;')
            return await self.fetch_all_as_dict(cursor)

    async def get_existing_score(self, user_id) -> int | None:
        async with aiosqlite.connect(self.resolved_db_path) as connection:
            cursor = await connection.execute('SELECT score FROM GeoguessrLeaderboard WHERE user_id = ? LIMIT 1;',
                                              (user_id,))
            dictionary = await self.fetch_first_as_dict(cursor)
            if not dictionary:
                return None
            return int(dictionary['score'])

    async def add_into(self, user_id, score):
        async with aiosqlite.connect(self.resolved_db_path) as connection:
            await connection.execute('INSERT INTO GeoguessrLeaderboard (user_id, score) values (?, ?);',
                                     (user_id, score))
            await connection.commit()

    async def get_by_userid_scores_descending(self, user_id: int):
        async with aiosqlite.connect(self.resolved_db_path) as connection:
            cursor = await connection.execute('SELECT * FROM GeoguessrLeaderboard WHERE user_id = ? '
                                              'ORDER BY score DESC LIMIT 1;', (user_id,))
            dictionary = await self.fetch_first_as_dict(cursor)
            if not dictionary:
                return None
            return GeoguessrLeaderboard(**dictionary)
