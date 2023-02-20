import logging

import discord
from discord import Interaction, TextStyle
from discord.ui import Modal, TextInput

from bot.consts import Colors
from bot.data.class_repository import ClassRepository
from bot.messaging.events import Events
from bot.models.class_models import ClassChannelScaffold
from bot.sock_bot import SockBot
from bot.utils.helpers import error_embed

log = logging.Logger(__name__)


class AddClassModal(Modal):

    category = TextInput(
        label='Course Major',
        default='cpsc',
        placeholder='cpsc',
        min_length=3,
        max_length=4,
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
        min_length=5,
        max_length=50,
        row=2
    )
    professor = TextInput(
        label='Course Instructor',
        placeholder='Dean',
        min_length=2,
        max_length=15,
        row=3
    )
    course_description = TextInput(
        label='Course Description',
        placeholder='Students learn about...',
        style=TextStyle.long,
        max_length=250,
        required=False,
        row=4
    )

    def __init__(self, bot: SockBot,
                 *,
                 class_data: tuple[str, int] | None = None,
                 channel: discord.TextChannel | None = None):
        super().__init__(title='📔 Add Class' if not channel else f'Insert #{channel.name}')
        self._bot = bot
        self._channel = channel
        self._repo = ClassRepository()
        if class_data:
            prefix, num = class_data
            self.category.default = prefix
            self.course_number.default = num
        if channel:
            split_topic = channel.topic.split('-') if channel.topic else []
            split_name = channel.name.split('-')
            if len(split_name) == 3:  # Autofill where possible
                if 3 <= len(split_name[0]) <= 4:
                    self.category.default = split_name[0].upper()
                if len(split_name[1]) == 4 and split_name[1].isdigit():
                    self.course_number.default = split_name[1]
                self.professor.default = split_name[2].title()
            if len(split_topic) == 2:
                self.course_title.default = split_topic[0].title().strip()
                self.course_description.default = split_topic[1].strip()

    async def on_submit(self, inter: Interaction) -> None:
        # correct for error - reject if invalid
        if not self.course_number.value.isdigit():
            embed = error_embed(inter.user, f'Course number `{self.course_number.value}` is invalid.')
            await inter.response.send_message(embed=embed, ephemeral=True)
        # format our data correctly
        professor = self.professor.value.split(' ')[-1].title()
        title = self.course_title.value.title()
        prefix = self.category.value.upper()
        description = self.course_description.value.capitalize()
        # check if a similar class exists
        if await self._search_similar(inter, prefix, int(self.course_number.value), professor):
            return
        # create a new class channel scaffold to send to the service
        scaffold = ClassChannelScaffold(class_prefix=prefix,
                                        class_name=title,
                                        class_number=int(self.course_number.value),
                                        class_professor=professor)
        if self._channel:
            await self._bot.messenger.publish(Events.on_class_insert, inter, scaffold, self._channel, description)
        else:
            await self._bot.messenger.publish(Events.on_class_create, inter, scaffold, description)

    async def _search_similar(self, inter: discord.Interaction, pref: str, num: int, prof: str) -> bool:
        similar_class = await self._repo.search_class(pref, num, prof)
        if not similar_class:
            return False
        channel = self._bot.guild.get_channel(similar_class.channel_id)
        if channel and not similar_class.class_archived:
            if role := self._bot.guild.get_role(similar_class.class_role_id):
                await inter.user.add_roles(role)
            embed = discord.Embed(title='📔 Similar Class Found', color=Colors.Purple)
            embed.description = f'A similar class channel has been found.'
            if role:
                embed.description += f'\nThe {role.mention} role has been added to you.'
            embed.add_field(name='Channel', value=channel.mention)
            embed.add_field(name='Class Instructor', value=similar_class.class_professor)
            embed.add_field(name='Class Name', value=similar_class.full_title(), inline=False)
            await inter.response.send_message(embed=embed)
            return True
        if channel and similar_class.class_archived:
            await self._bot.messenger.publish(Events.on_class_unarchive, inter, similar_class)
            return True
        return False
