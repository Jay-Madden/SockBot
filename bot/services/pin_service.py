import discord
from discord import RawMessageDeleteEvent, RawReactionActionEvent

from bot.consts import Staff
from bot.data.class_repository import ClassRepository
from bot.data.pin_repository import PinRepository
from bot.messaging.events import Events
from bot.services.base_service import BaseService
from bot.sock_bot import SockBot
from bot.utils.helpers import fetch_optional_message

PIN_REACTION = '📌'
MIN_PIN_REACTIONS = 5
MAX_PINS_PER_CHANNEL = 50


class PinService(BaseService):

    def __init__(self, bot: SockBot):
        super().__init__(bot)
        self.pin_repo = PinRepository()
        self.class_repo = ClassRepository()

    @BaseService.listener(Events.on_raw_reaction_add)
    async def on_raw_reaction(self, event: RawReactionActionEvent):
        # using on_raw_reaction_add event because on_reaction_add only works if the message is cached
        # which ends up missing a lot of reactions for messages that are not cached
        if event.member.bot or event.emoji.name != PIN_REACTION or event.event_type != 'REACTION_ADD':
            return
        if not (class_pin := await self.pin_repo.get_open_pin_from_message(event.message_id)):
            return

        # fetch the channel, message, reaction
        if not (channel := self.bot.guild.get_channel(event.channel_id)):
            return
        message = await channel.fetch_message(event.message_id)
        react: discord.Reaction | None = None
        for reaction in message.reactions:
            if reaction.emoji == PIN_REACTION:
                react = reaction
                break
        assert react is not None

        # check if one of our conditions is met to pin the message
        if react.count >= MIN_PIN_REACTIONS or Staff.is_staff(event.member):
            if not (to_pin := await fetch_optional_message(channel, class_pin.user_message_id)):
                await message.delete()
                await self.pin_repo.delete_pin(class_pin)
                return
            # check if we have enough space to pin
            pinned_messages = await channel.pins()
            # unpin the oldest pin if there is no room
            if len(pinned_messages) == MAX_PINS_PER_CHANNEL:
                await pinned_messages[-1].unpin(reason='Unpinned to make room.')
            # pin the message, update the pin in the db, and delete sockbot's pin request embed
            await to_pin.pin(reason=f'Pinned by vote, started by user with ID {class_pin.pin_requester}')
            await self.pin_repo.set_pinned(class_pin)
            await message.delete()

    @BaseService.listener(Events.on_raw_message_delete)
    async def on_message_delete(self, payload: RawMessageDeleteEvent):
        # using the on_raw_message_delete event because on_message_delete ignores SockBot's messages being deleted
        # check if the message was in our db (either sockbot's embed or to-be-pinned message)
        if not (class_pin := await self.pin_repo.get_open_pin_from_message(payload.message_id)):
            return
        await self.pin_repo.delete_pin(class_pin)

    @BaseService.listener(Events.on_guild_channel_delete)
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
            # if the message was pinned while we were offline, set it as pinned in the db
            if message.pinned:
                await self.pin_repo.set_pinned(class_pin)
