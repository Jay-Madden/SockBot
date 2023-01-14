from discord import Interaction, SelectOption, TextStyle
from discord.ui import Modal, TextInput, Select


class ClassModal(Modal):

    CPSC = SelectOption(label='Computer Science', value='cpsc', default=True)
    HCC = SelectOption(label='Human Centered Computing', value='hcc')
    MATH = SelectOption(label='Mathematics', value='math')

    category = Select(placeholder='Select Class Category', options=[CPSC, HCC, MATH], row=0)
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

    def __init__(self):
        super().__init__(title='Add Class', timeout=350)

    async def on_submit(self, interaction: Interaction) -> None:
        # correct for error - reject if invalid
        pass
