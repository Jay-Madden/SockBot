import calendar
from datetime import datetime
from typing import Literal, Union

import discord
from discord import NotFound

from bot.consts import Colors
from bot.messaging.events import Events
from bot.sock_bot import SockBot

DATE_FORMAT = '%Y-%m-%d %H:%M:%S'


def strtodt(date: str) -> datetime:
    """A simple util for translating UTC timestamps in the database to UTC datetime.datetime objects."""
    return datetime.strptime(date, DATE_FORMAT)


def as_timestamp(date: datetime, /, style: Literal["f", "F", "d", "D", "t", "T", "R"] = "f") -> str:
    """
    Formats the given datetime to a Discord timestamp.
    Used over discord.utils.format_dt due to incorrect timestamp output.
    """
    timestamp = calendar.timegm(date.utctimetuple())
    return f'<t:{timestamp}:{style}>'


def error_embed(author: Union[discord.User, discord.Member], description: str) -> discord.Embed:
    """
    Shorthand for sending an error message with consistent formatting.
    """
    embed = discord.Embed(title='Error', color=Colors.Error, description=description)
    embed.set_footer(text=str(author), icon_url=author.display_avatar.url)
    return embed


async def deletable_error_embed(bot: SockBot, ctx, description: str) -> None:
    embed = error_embed(ctx.author, description)
    msg = await ctx.send(embed=embed)
    await bot.messenger.publish(
        Events.on_set_deletable, msg=msg, author=ctx.author, timeout=60
    )


async def fetch_optional_message(channel: discord.TextChannel, message_id: int) -> discord.Message | None:
    """
    Tries to fetch a discord.Message object from the given channel.
    If discord.errors.NotFound is raised, the method will return None.
    """
    try:
        return await channel.fetch_message(message_id)
    except NotFound:
        return None
