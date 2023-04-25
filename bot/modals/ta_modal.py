from discord.ui import Modal, TextInput

from bot.models.class_models import ClassTA, ClassChannel


class TAModal(Modal):

    details = TextInput(
        label='TA Details',
        placeholder='List the class, office hours, your email, and any other info you would like students to know!',
        max_length=1000
    )

    def __init__(self, cls: ClassChannel, class_ta: ClassTA, display_tag: bool):
        super().__init__(title=f'Edit TA Details for {cls.channel_name}')
        self._display_tag = display_tag
        if class_ta.ta_details:
            self.details.default = class_ta.ta_details
