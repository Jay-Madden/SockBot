import discord
from discord.ext import commands

import bot.extensions as ext
from bot.consts import Colors
from bot.data.class_repository import ClassRepository
from bot.messaging.events import Events
from bot.sock_bot import SockBot
from bot.utils.helpers import deletable_error_embed


class PinCog(commands.Cog):

    def __init__(self, bot: SockBot) -> None:
        self.bot = bot
        self.repo = ClassRepository()

    @ext.command(case_insensitive=True)
    @ext.long_help('Create a pin request in your class channel.')
    async def pin(self, ctx, message: discord.Message | None = None) -> None:
        message = message if message else ctx.message.reference
        if not message:
            await deletable_error_embed(self.bot, ctx, 'Reply to a message or give the ID or link to a message.')
            return
        if not (sent_channel := await self.repo.search_class_by_channel(ctx.channel.id)):
            await deletable_error_embed(self.bot, ctx, 'Please use this command in a class channel only.')
            return
        if not (class_channel := await self.repo.search_class_by_channel(message.channel.id)):
            await deletable_error_embed(self.bot, ctx, 'Cannot pin message from non-class channel.')
            return
        if sent_channel != class_channel:
            await deletable_error_embed(self.bot, ctx, 'Open a pin request in the same channel that the message is in.')
            return
        if message.pinned:
            await deletable_error_embed(self.bot, ctx, 'The message given is already pinned.')
            return
        assert isinstance(class_channel, discord.TextChannel)
        if request := await self.repo.get_pin_request(message):
            request_message = class_channel.get_partial_message(request.pin_message_id)
            embed = discord.Embed(title='Pin Request Already Exists', color=Colors.Error)
            embed.description = 'A pin request for this message has already been created.'
            embed.add_field(name='Request Link', value=f'[Link]({request_message.jump_url})')
            requester = self.bot.get_user(request.pin_requester)
            if requester:
                embed.add_field(name='Requested By', value=requester.mention)
            await ctx.send(embed=embed)
        await self.bot.messenger.publish(Events.on_pin_request, ctx, message)


async def setup(bot: SockBot) -> None:
    await bot.add_cog(PinCog(bot))
