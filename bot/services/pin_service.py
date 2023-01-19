from typing import Union

import discord

from bot.messaging.events import Events
from bot.services.base_service import BaseService
from bot.sock_bot import SockBot


class PinService(BaseService):

    def __init__(self, *, bot: SockBot):
        super().__init__(bot)

    @BaseService.Listener(Events.on_reaction_add)
    async def on_reaction_add(self, react: discord.Reaction, user: Union[discord.User, discord.Member]):

        pass

    def load_service(self):
        pass
