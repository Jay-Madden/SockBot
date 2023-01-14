import discord
from discord import Interaction, TextStyle
from discord.ui import Modal, TextInput


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

    def __init__(self, pref: str | None = None, num: int | None = None):
        super().__init__(title='📔 Add Class', timeout=350)
        if pref:
            self.category.default = pref
        if num:
            self.course_number.default = str(num)

    async def on_submit(self, interaction: Interaction) -> None:
        # correct for error - reject if invalid
        pass


class InsertClassModal(Modal):

    why = TextInput(
        label='Why?',
        placeholder='Because...',
        style=TextStyle.long,
        max_length=250,
        required=False
    )

    def __init__(self, channel: discord.TextChannel) -> None:
        super().__init__(title=f'Insert #{channel.name}')

    async def on_submit(self, interaction: Interaction) -> None:
        pass
