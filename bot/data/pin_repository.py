from typing import Union

import aiosqlite
import discord

from bot.data.base_repository import BaseRepository
from bot.models.class_models import ClassPin


class PinRepository(BaseRepository):

    async def get_active_pins(self) -> list[ClassPin]:
        """
        Fetches all ClassPin's that are currently not pinned.
        """
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute('SELECT * FROM ClassPin WHERE pin_pinned = FALSE')
            return [ClassPin(**d) for d in await self.fetcthall_as_dict(cursor)]

    async def get_pin_request(self, pinned_message: Union[int, discord.Message]) -> ClassPin | None:
        """
        Searches for a class pin request given the message (to be pinned) ID or message itself.
        """
        message_id = pinned_message if isinstance(pinned_message, int) else pinned_message.id
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute('SELECT * FROM ClassPin WHERE original_post_message_id = ?', (message_id,))
            dictionary = await self.fetcthone_as_dict(cursor)
            if not len(dictionary):
                return None
            return ClassPin(**dictionary)

    async def set_pinned(self, pinned_message: ClassPin) -> None:
        async with aiosqlite.connect(self.resolved_db_path) as db:
            await db.execute('UPDATE ClassPin SET pin_pinned = TRUE WHERE original_post_message_id = ?',
                             (pinned_message.original_post_message_id,))
            await db.commit()

    async def insert_pin(self, pin: ClassPin) -> None:
        async with aiosqlite.connect(self.resolved_db_path) as db:
            await db.execute('INSERT INTO ClassPin VALUES (?, ?, ?, ?, ?, False)',
                             (pin.pin_message_id, pin.original_post_message_id, pin.channel_id,
                              pin.pin_owner, pin.pin_requester))
            await db.commit()
