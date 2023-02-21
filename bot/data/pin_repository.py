from typing import Union

import aiosqlite
import discord

from bot.data.base_repository import BaseRepository
from bot.models.class_models import ClassPin


class PinRepository(BaseRepository):

    async def get_open_pin_requests(self) -> list[ClassPin]:
        """
        Fetches all ClassPin's that are currently not pinned.
        """
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute('SELECT * FROM ClassPin WHERE pin_pinned = FALSE')
            return [ClassPin(**d) for d in await self.fetcthall_as_dict(cursor)]

    async def get_pin_from_sockbot(self, message: Union[int, discord.Message]) -> ClassPin | None:
        """
        Searches for a class pin from the given message.
        The given message should have been sent by SockBot, not another user.
        To search for a pin request from the to-be-pinned message (sent by a user), use `get_pin_from_message()`
        """
        message_id = message if isinstance(message, int) else message.id
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute('SELECT * FROM ClassPin WHERE sockbot_message_id = ?', (message_id,))
            dictionary = await self.fetcthone_as_dict(cursor)
            if not len(dictionary):
                return None
            return ClassPin(**dictionary)

    async def get_pin_from_user(self, message: Union[int, discord.Message]) -> ClassPin | None:
        """
        Searches for a class pin from the given message.
        The given message should be the to-be-pinned message (sent by a user).
        To search for a pin request from SockBot's pin request embed, use `get_pin_from_sockbot()`
        """
        message_id = message if isinstance(message, int) else message.id
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute('SELECT * FROM ClassPin WHERE user_message_id = ?', (message_id,))
            dictionary = await self.fetcthone_as_dict(cursor)
            if not len(dictionary):
                return None
            return ClassPin(**dictionary)

    async def get_pins_from_channel(self, channel: Union[int, discord.TextChannel]) -> list[ClassPin]:
        """
        Searches for all class pins that are in the given channel.
        """
        channel_id = channel if isinstance(channel, int) else channel.id
        async with aiosqlite.connect(self.resolved_db_path) as db:
            cursor = await db.execute('SELECT * FROM ClassPin WHERE channel_id = ?', (channel_id,))
            return [ClassPin(**d) for d in await self.fetcthall_as_dict(cursor)]

    async def set_pinned(self, pinned_message: ClassPin) -> None:
        """
        Updates the given ClassPin in the database.
        Sets pin_pinned = True
        """
        async with aiosqlite.connect(self.resolved_db_path) as db:
            await db.execute('UPDATE ClassPin SET pin_pinned = TRUE WHERE sockbot_message_id = ?',
                             (pinned_message.sockbot_message_id,))
            await db.commit()

    async def insert_pin(self, pin: ClassPin) -> None:
        """
        Inserts the given ClassPin into the database.
        """
        async with aiosqlite.connect(self.resolved_db_path) as db:
            await db.execute('INSERT INTO ClassPin VALUES (?, ?, ?, ?, ?, False)',
                             (pin.sockbot_message_id, pin.user_message_id,
                              pin.channel_id, pin.pin_owner, pin.pin_requester))
            await db.commit()

    async def delete_pin(self, pin: ClassPin) -> None:
        """
        Deletes the given ClassPin from the database.
        """
        async with aiosqlite.connect(self.resolved_db_path) as db:
            await db.execute('DELETE FROM ClassPin WHERE sockbot_message_id = ?', (pin.sockbot_message_id,))
            await db.commit()

