import discord
from discord.ext import commands

import bot.extensions as ext
from bot.consts import Colors
from bot.data.class_repository import ClassRepository
from bot.data.pin_repository import PinRepository
from bot.messaging.events import Events
from bot.sock_bot import SockBot
from bot.utils.helpers import deletable_error_embed


class PinCog(commands.Cog):

    def __init__(self, bot: SockBot) -> None:
        self.bot = bot
        self.class_repo = ClassRepository()
        self.pin_repo = PinRepository()

    @ext.command(case_insensitive=True)
    @ext.short_help('Open a pin request.')
    @ext.long_help('Open a request to get a message pinned in your class channel.')
    @ext.example(['pin https://discord.com/...'])
    async def pin(self, ctx, message: discord.Message | None = None) -> None:
        if not message and ctx.message.reference:
            message = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        if not message:
            await deletable_error_embed(self.bot, ctx, 'Reply to a message or give the ID or link to a message.')
            return
        if message.pinned:
            await deletable_error_embed(self.bot, ctx, 'The message given is already pinned.')
            return
        if message.author.bot:
            await deletable_error_embed(self.bot, ctx, 'Cannot pin a bot message.')
            return
        if not (sent_channel := await self.class_repo.search_class_by_channel(ctx.channel.id)):
            await deletable_error_embed(self.bot, ctx, 'Please use this command in a class channel only.')
            return
        if not (message_channel := await self.class_repo.search_class_by_channel(message.channel.id)):
            await deletable_error_embed(self.bot, ctx, 'Cannot pin message from non-class channel.')
            return
        if sent_channel.channel_id != message_channel.channel_id:
            await deletable_error_embed(self.bot, ctx, 'Open a pin request in the same channel that the message is in.')
            return
        if sent_channel.class_archived:
            await deletable_error_embed(self.bot, ctx, 'Cannot open a pin request in an archived channel.')
            return
        # check to see if a class pin already exists for the given message
        if class_pin := await self.pin_repo.get_pin_from_user(message):
            request_message = message.channel.get_partial_message(class_pin.sockbot_message_id)
            embed = discord.Embed(title='📌 Pin Request Already Exists', color=Colors.Error)
            embed.description = 'A pin request for this message has already been created.'
            embed.add_field(name='Request Link', value=f'[Link]({request_message.jump_url})')
            requester = self.bot.get_user(class_pin.pin_requester)
            if requester:
                embed.add_field(name='Requested By', value=requester.mention)
            embed.set_footer(text=str(ctx.author), icon_url=ctx.author.display_avatar)
            message = await ctx.send(embed=embed)
            await ctx.message.delete()
            await self.bot.messenger.publish(Events.on_set_deletable, msg=message, author=ctx.author)
            return
        await self.bot.messenger.publish(Events.on_pin_request, ctx, message)


async def setup(bot: SockBot) -> None:
    await bot.add_cog(PinCog(bot))
