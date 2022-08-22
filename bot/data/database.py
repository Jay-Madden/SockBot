import logging
import os
from pathlib import Path

import aiosqlite

log = logging.getLogger(__name__)


class Database:
    async def create_database(self):
        if not os.path.exists('database'):
            log.info('Database Folder not found: Creating one')
            os.makedirs('database')
        async with aiosqlite.connect(Path(f'database/SockBot.db')) as db:
            with open('bot/data/CreateTables.sql') as f:
                await db.executescript(f.read())
                await db.commit()
