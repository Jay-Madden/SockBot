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

    def __init__(self, *, class_data: tuple[str, int] | None = None, channel: discord.TextChannel | None = None):
        super().__init__(title='📔 Add Class' if not channel else f'Insert #{channel.name}', timeout=350)
        self._channel = channel
        if class_data:
            prefix, num = class_data
            self.category.default = prefix
            self.course_number.default = num
        if channel:
            split = channel.name.split('-')
            if len(split) == 3:  # Autofill where possible
                if 3 <= len(split[0]) <= 4:
                    self.category.default = split[0]
                if len(split[1]) == 4 and split[1].isdigit():
                    self.course_number.default = split[1]
                self.professor.default = split[2]

    async def on_submit(self, interaction: Interaction) -> None:
        # correct for error - reject if invalid

        pass
