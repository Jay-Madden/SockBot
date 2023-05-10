import discord
from discord import TextStyle
from discord.ui import Modal, TextInput

from bot.consts import Colors
from bot.data.class_repository import ClassRepository
from bot.models.class_models import ClassTA, ClassChannel
from bot.sock_bot import SockBot


class TAModal(Modal):

    details = TextInput(
        label='TA Details',
        style=TextStyle.long,
        placeholder='List the class, office hours, your email, and any other info you would like students to know!',
        max_length=1000,
        required=False
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

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await self._bot.on_modal_error(interaction, error)

    async def on_submit(self, inter: discord.Interaction) -> None:
        self._class_ta.ta_details = self.details.value.strip()
        self._class_ta.ta_display_tag = self._display_tag
        await self._repo.update_ta(self._class_ta)

        # send our embed
        embed = discord.Embed(title='📔 TA Details Updated', color=Colors.Purple)
        embed.description = f'Your TA details have been updated for {self._cls.full_title}.'
        if self._class_ta.has_details:
            embed.add_field(name='Details', value=self._class_ta.ta_details)
        await inter.response.send_message(embed=embed, ephemeral=True)
