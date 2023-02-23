from typing import Union

import discord
from discord import RawMessageDeleteEvent
from discord.ext.commands import Context

from bot.consts import Staff, Colors
from bot.data.class_repository import ClassRepository
from bot.data.pin_repository import PinRepository
from bot.messaging.events import Events
from bot.models.class_models import ClassPin
from bot.services.base_service import BaseService
from bot.sock_bot import SockBot
from bot.utils.helpers import fetch_optional_message

PIN_REACTION = '📌'
MIN_PIN_REACTIONS = 5
MAX_CONTENT_CHARS = 250
MAX_PINS_PER_CHANNEL = 50


class PinService(BaseService):

    def __init__(self, *, bot: SockBot):
        super().__init__(bot)
        self.pin_repo = PinRepository()
        self.class_repo = ClassRepository()

    @BaseService.Listener(Events.on_pin_request)
    async def on_pin_request(self, ctx: Context, message: discord.Message):
        # format our message content
        if len(message.content) > MAX_CONTENT_CHARS:
            content = message.content[:MAX_CONTENT_CHARS] + '...'
        else:
            content = message.content
        # prepare our embed
        embed = discord.Embed(title='📌 Pin Request', color=Colors.Purple)
        embed.description = f'{ctx.author.mention} wants to pin a message.\n' \
                            f'Click the {PIN_REACTION} reaction below to pin this message.'
        embed.add_field(name='Content', value=content, inline=False)
        embed.add_field(name='Author', value=message.author.mention)
        embed.add_field(name='Message Link', value=f'[Link]({message.jump_url})')
        if len(message.attachments):
            embed.add_field(name='Files Attached', value=len(message.attachments))
        sockbot_message = await message.channel.send(embed=embed)
        await sockbot_message.add_reaction(PIN_REACTION)
        # create our class pin object and push it to the db
        class_pin = ClassPin(sockbot_message.id, message.id, message.channel.id, message.author.id, ctx.author.id)
        await self.pin_repo.insert_pin(class_pin)
        # finally, delete the command sent to us
        await ctx.message.delete()

    @BaseService.Listener(Events.on_reaction_add)
    async def on_reaction_add(self, react: discord.Reaction, user: Union[discord.User, discord.Member]):
        if react.emoji != PIN_REACTION:
            return
        if not (class_pin := await self.pin_repo.get_pin_from_sockbot(react.message)):
            return
        if react.count >= MIN_PIN_REACTIONS or Staff.is_staff(user):
            channel = react.message.channel
            # make sure our message to-be-pinned still exists
            if not (to_pin := await fetch_optional_message(channel, class_pin.user_message_id)):
                await react.message.delete()
                await self.pin_repo.delete_pin(class_pin)
                return
            # check if we have enough space to pin
            pinned_messages = await channel.pins()
            # unpin the oldest pin if there is no room
            if len(pinned_messages) == MAX_PINS_PER_CHANNEL:
                await pinned_messages[0].unpin(reason='Unpinned to make room.')
            # pin the message, update the pin in the db, and delete sockbot's pin request embed
            await to_pin.pin(reason='Pinned by `pin` command.')
            await self.pin_repo.set_pinned(class_pin)
            await react.message.delete()

    @BaseService.Listener(Events.on_raw_message_delete)
    async def on_message_delete(self, payload: RawMessageDeleteEvent):
        # using the on_raw_message_delete event because on_message_delete ignores self-posts
        # check if the message was in our db (either sockbot's embed or to-be-pinned message)
        if not (class_pin := await self.pin_repo.get_open_pin_from_message(payload.message_id)):
            return
        await self.pin_repo.delete_pin(class_pin)

    @BaseService.Listener(Events.on_guild_channel_delete)
    async def on_channel_delete(self, channel: discord.TextChannel):
        for pin in await self.pin_repo.get_pins_from_channel(channel):
            await self.pin_repo.delete_pin(pin)

    async def load_service(self):
        for class_pin in await self.pin_repo.get_open_pin_requests():
            # make sure channel still exists
            if not (channel := self.bot.guild.get_channel(class_pin.channel_id)):
                await self.pin_repo.delete_pin(class_pin)
                continue
            # make sure that the embed sent by SockBot still exists
            if not await fetch_optional_message(channel, class_pin.sockbot_message_id):
                await self.pin_repo.delete_pin(class_pin)
                continue
            # make sure the message to-be-pinned still exists
            if not (message := await fetch_optional_message(channel, class_pin.user_message_id)):
                await self.pin_repo.delete_pin(class_pin)
                continue
            if message.pinned:
                await self.pin_repo.set_pinned(class_pin)
