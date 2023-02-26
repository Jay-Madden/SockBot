import logging

import discord

from bot.messaging.events import Events
from bot.services.base_service import BaseService

log = logging.getLogger(__name__)


class MessageHandlingService(BaseService):

    def __init__(self, *, bot):
        super().__init__(bot)

    @BaseService.listener(Events.on_guild_message_received)
    async def on_guild_message_received(self, message: discord.Message) -> None:
        # Primary entry point for handling commands
        await self.bot.process_commands(message)

    async def load_service(self):
        pass
