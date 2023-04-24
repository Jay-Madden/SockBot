from typing import Union, Callable

import discord
from discord import Interaction, TextStyle
from discord.ui import Modal, TextInput

from bot.consts import Colors
from bot.data.class_repository import ClassRepository
from bot.messaging.events import Events
from bot.models.class_models import ClassChannelScaffold
from bot.sock_bot import SockBot
from bot.utils.helpers import error_embed

# Min and max of major length, i.e., 'CPSC', 'HCC', 'MATH'
MIN_MAJOR_LEN = 3
MAX_MAJOR_LEN = 4
# Min and max of class title length, i.e., 'Data Structures and Algorithms', etc.
MIN_TITLE_LEN = 5
MAX_TITLE_LEN = 50
# Min and max of class instructor, i.e., 'Dean', 'Widman', 'VanScoy', etc.
MIN_INSTR_LEN = 2
MAX_INSTR_LEN = 15
# Max length of class description, i.e., 'Students learn about...'
MAX_DESCR_LEN = 500
# Min and max of class number, i.e., 1060, 4910, 8400, etc.
MIN_CLASS_NUM = 1000
MAX_CLASS_NUM = 8999

ADD = lambda data: '📔 Add Class'
EDIT = lambda data: f'📔 Edit #{data[0].name}'
INSERT = lambda data: f'📔 Insert #{data[0].name}'

CLASS_DATA = Union[tuple[str, int], tuple[discord.TextChannel, discord.Role]]


class ClassModal(Modal):

    major = TextInput(
        label='Course Major',
        default='cpsc',
        placeholder='cpsc',
        min_length=MIN_MAJOR_LEN,
        max_length=MAX_MAJOR_LEN,
        row=0
    )
    course_number = TextInput(
        label='Course Number',
        placeholder='2120',
        min_length=4,
        max_length=4,
        row=1
    )
    course_title = TextInput(
        label='Course Name',
        placeholder='Data Structures & Algorithms',
        min_length=MIN_TITLE_LEN,
        max_length=MAX_TITLE_LEN,
        row=2
    )
    professor = TextInput(
        label='Course Instructor',
        placeholder='Dean',
        min_length=MIN_INSTR_LEN,
        max_length=MAX_INSTR_LEN,
        row=3
    )
    course_description = TextInput(
        label='Course Description',
        placeholder='Students learn about...',
        style=TextStyle.long,
        max_length=MAX_DESCR_LEN,
        required=False,
        row=4
    )

    def __init__(self, bot: SockBot,
                 *,
                 mode: Callable[[CLASS_DATA], str] = ADD,
                 class_data: CLASS_DATA | None = None):
        super().__init__(title=mode(class_data))
        self._bot = bot
        self._mode = mode
        self._data = class_data
        self._repo = ClassRepository()
        if class_data:
            self._autofill(class_data)

    async def on_submit(self, inter: Interaction) -> None:
        # correct for error - reject if invalid
        if not valid_course_num(self.course_number.value):
            embed = error_embed(inter.user, f'Course number `{self.course_number.value}` is invalid.')
            await inter.response.send_message(embed=embed, ephemeral=True)
            return
        # format our data, so it's nice and neat and capitalized correctly (I know you guys don't use caps)
        professor = self.professor.value.split()[-1].capitalize()
        title = self.course_title.value.title()
        major = self.major.value.upper()
        description = self.course_description.value.capitalize()
        number = int(self.course_number.value)

        # create a new class channel scaffold to send to the service
        scaffold = ClassChannelScaffold(class_prefix=major,
                                        class_name=title,
                                        class_number=number,
                                        class_professor=professor)

        if self._mode == EDIT:
            await self._bot.messenger.publish(
                Events.on_class_edit, inter, scaffold, role=self._data[1], desc=description
            )
            return

        # check if a similar class exists
        if await self._search_similar(inter, major, number, professor):
            return

        if self._mode == INSERT:
            await self._bot.messenger.publish(
                Events.on_class_insert, inter, scaffold, self._data[0], role=self._data[1], desc=description
            )
        else:
            await self._bot.messenger.publish(Events.on_class_create, inter, scaffold, description)

    async def on_error(self, interaction: Interaction, error: Exception) -> None:
        await self._bot.on_modal_error(interaction, error)

    async def _search_similar(self, inter: discord.Interaction, pref: str, num: int, prof: str) -> bool:
        """
        Searches for a similar class with the given major, course number, and instructor.

        Returns True if:
        - A similar class, that already exists and is unarchived, is found.
        - A similar class that already exists, but is archived.

        Returns False otherwise.
        """
        if not (similar_class := await self._repo.search_class(pref, num, prof)):
            return False

        channel = self._bot.guild.get_channel(similar_class.channel_id)

        # if the channel exists and the class is unarchived, add the class role & send the embed
        if channel and not similar_class.class_archived:
            if role := self._bot.guild.get_role(similar_class.class_role_id):
                await inter.user.add_roles(role)
            embed = discord.Embed(title='📔 Similar Class Found', color=Colors.Purple)
            embed.description = 'A similar class channel has been found.'
            if role:
                embed.description += f'\nThe {role.mention} role has been added to you.'
            embed.add_field(name='Channel', value=channel.mention)
            embed.add_field(name='Instructor', value=similar_class.class_professor)
            embed.add_field(name='Class Title', value=similar_class.full_title, inline=False)
            await inter.response.send_message(embed=embed)
            return True

        # if a channel exists, but the class is archived - publish unarchive event for our similar class
        if channel and similar_class.class_archived:
            await self._bot.messenger.publish(Events.on_class_unarchive, inter, similar_class)
            return True

        # a similar class was found in the database, but the paired channel doesn't exist...
        # the method should never reach this point though, since class channels that have no existing
        # channel are purged from the database upon startup of SockBot (as well as in a listener)
        return False

    def _autofill(self, data: CLASS_DATA) -> None:
        """
        Automatically fills in the defaults of our items with our given data.
        If `tuple[str, int]` is given as our data, we can fill:
        - major
        - course_number

        If `tuple[discord.TextChannel, discord.Role]` is given as our data, we can fill some or all items, given:
        - The name of the channel is formatted as `MAJR-XXXX-[Professor]`
        - The topic of the channel is formatted as `[Course Title] - [Course Description]`
        """
        if isinstance(data[0], str):
            prefix, num = data
            self.major.default = prefix
            self.course_number.default = num
            return

        split_topic = data[0].topic.split('-') if data[0].topic else []
        split_name = data[0].name.split('-')

        # fill in the data from our split channel name, if possible
        if len(split_name) >= 3:
            if valid_course_maj(split_name[0]):
                self.major.default = split_name[0].upper()
            if valid_course_num(split_name[1]):
                self.course_number.default = split_name[1].strip()
            self.professor.default = split_name[-1].strip().capitalize()[:MAX_INSTR_LEN]

        # fill in the data from our split channel topic, if possible
        if len(split_topic) == 2:
            self.course_title.default = split_topic[0].title().strip()[:MAX_TITLE_LEN]
            description = split_topic[1].strip()[:MAX_DESCR_LEN]
            self.course_description.default = description or 'None'


def valid_course_maj(course_maj: str) -> bool:
    return MIN_MAJOR_LEN <= len(course_maj) <= MAX_MAJOR_LEN


def valid_course_num(course_num: Union[str, int]) -> bool:
    if isinstance(course_num, str) and not course_num.isdigit():
        return False

    return MIN_CLASS_NUM <= int(course_num) <= MAX_CLASS_NUM
