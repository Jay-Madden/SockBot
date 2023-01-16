import calendar
from datetime import datetime
from typing import Literal, Union

import discord

from bot.consts import Colors


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
