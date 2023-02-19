from typing import Union

import discord

from bot.consts import Staff
from bot.data.pin_repository import PinRepository
from bot.messaging.events import Events
from bot.models.class_models import ClassPin
from bot.services.base_service import BaseService
from bot.sock_bot import SockBot

MAX_PINS_PER_CHANNEL = 50
MIN_PIN_REACTIONS = 5  # 4 + 1 (SockBot)
PIN_REACTION = '📌'


class PinService(BaseService):

    def __init__(self, *, bot: SockBot):
        super().__init__(bot)
        self.repo = PinRepository()
        self.pin_requests: list[ClassPin] = []

    @BaseService.Listener(Events.on_reaction_add)
    async def on_reaction_add(self, react: discord.Reaction, user: Union[discord.User, discord.Member]):
        if not (class_pin := await self.repo.get_pin_request(react.message.id)):
            return
        if react.count >= MIN_PIN_REACTIONS or Staff.is_staff(user):
            # check if we have enough space to pin
            channel = react.message.channel
            pinned_messages = await channel.pins()
            if len(pinned_messages) == MAX_PINS_PER_CHANNEL:
                # unpin the oldest pin
                await pinned_messages[0].unpin(reason='Unpinned to make room.')
            await react.message.pin(reason='Pinned by ?pin command.')
            # todo edit pin message embed
            await self.repo.set_pinned(class_pin)

    async def load_service(self):
        self.pin_requests.extend(await self.repo.get_active_pins())
