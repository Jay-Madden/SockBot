import discord
from discord.ui import Modal, TextInput

from bot.data.class_repository import ClassRepository
from bot.models.class_models import ClassTA, ClassChannel
from bot.sock_bot import SockBot


class TAModal(Modal):

    details = TextInput(
        label='TA Details',
        placeholder='List the class, office hours, your email, and any other info you would like students to know!',
        max_length=1000
    )

    def __init__(self, bot: SockBot, cls: ClassChannel, class_ta: ClassTA, display_tag: bool):
        super().__init__(title=f'TA Details for {cls.channel_name}')
        self._bot = bot
        self._cls = cls
        self._class_ta = class_ta
        self._display_tag = display_tag
        self._repo = ClassRepository()
        if class_ta.has_details:
            self.details.default = class_ta.ta_details

    def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await self._bot.on_modal_error(interaction, error)

    def on_submit(self, inter: discord.Interaction) -> None:

        pass
