import typing
from enum import Enum, auto

import discord


class Colors:
    """Hex Color values"""

    Error = 0xE20000
    Purple = 0x522D80


class Staff(Enum):
    jayy = 190858129188192257
    smathep = 216632498015305729
    emulator = 187974048167362560
    bren = 274004148276690944
    vi = 534558685008101409
    jacob = 223241609293201408

    @staticmethod
    def is_staff(user: typing.Union[discord.User, discord.Member, int]) -> bool:
        # for testing purposes, I'm going to leave this in:
        if isinstance(user, discord.Member) and user.guild_permissions.administrator:
            return True
        user_id = user.id if isinstance(user, discord.User | discord.Member) else user
        return user_id in [s.value for s in Staff]


class DesignatedChannelBase(Enum):
    pass


class DesignatedChannels(DesignatedChannelBase):
    """Enum that defines possible designated channels for the bot to use"""

    message_log = auto()
    moderation_log = auto()
    startup_log = auto()
    user_join_log = auto()
    user_leave_log = auto()
    starboard = auto()

    @staticmethod
    def has(member: str) -> bool:
        return member in DesignatedChannels.__members__


class OwnerDesignatedChannels(DesignatedChannelBase):
    server_join_log = auto()
    error_log = auto()
    bot_dm_log = auto()

    @staticmethod
    def has(member: str) -> bool:
        return member in OwnerDesignatedChannels.__members__


class DiscordLimits:
    MessageLength = 1900
    EmbedFieldLength = 900

