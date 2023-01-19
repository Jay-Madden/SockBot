import logging

import discord
from discord import CategoryChannel

import bot.bot_secrets as bot_secrets
from bot.consts import Colors
from bot.data.class_repository import ClassRepository
from bot.errors import NoSemesterError
from bot.messaging.events import Events
from bot.models.class_models import ClassSemester, ClassChannel
from bot.services.base_service import BaseService
from bot.sock_bot import SockBot
from bot.utils.helpers import error_embed

log = logging.getLogger(__name__)
MAX_CHANNELS_PER_CATEGORY = 50


class ClassService(BaseService):

    def __init__(self, *, bot: SockBot):
        super().__init__(bot)
        self.repo = ClassRepository()
        self.semester: ClassSemester | None = None

    @BaseService.Listener(Events.on_class_create)
    async def on_class_create(self, ctx):
        if not self.semester:
            raise NoSemesterError(
                "**Unable to create class**: no semester is currently in session.\n"
                f"Type `{self.bot.current_prefix(ctx)}class semester` to see the upcoming semester start date."
            )

    @BaseService.Listener(Events.on_semester_archive)
    async def on_semester_archive(self, inter: discord.Interaction, semester: ClassSemester):
        class_guild = await self.repo.get_class_guild(inter.guild)
        notif_channel = self.bot.guild.get_channel(class_guild.notifications_channel_id)
        channels = await self.repo.get_semester_classes(semester)
        for channel in channels:
            category = self._available_archive_category()
            if not category and notif_channel:
                embed = discord.Embed(title='Error', color=Colors.Error)
                embed.description = f'Could not move #{channel.channel_name()}: No category to move to.'
                await notif_channel.send(embed=embed)
                return
            await self.on_class_archive(None, channel, category)
        if notif_channel:
            embed = discord.Embed(title='📔 Semester Archived', color=Colors.Purple)
            embed.description = f''

    @BaseService.Listener(Events.on_class_archive)
    async def on_class_archive(self,
                               inter: discord.Interaction | None,
                               cls: ClassChannel,
                               category: discord.CategoryChannel | None = None):
        pass

    async def _refresh_semester(self):
        self.semester = await self.repo.get_current_semester()
        if not self.semester:
            log.error('Refreshing the current semester resulted in None.')
            return
        # TODO: Announce that the semester is currently in session?

    def _available_archive_category(self) -> CategoryChannel | None:
        """
        Gets an archive category that has room for at least one channel.
        If None is returned, there are no archive categories that are not full.
        """
        archive_categories = bot_secrets.secrets.class_archive_category_ids
        for category in self.bot.guild.categories:
            if category.id not in archive_categories:
                continue
            if len(category.channels) < MAX_CHANNELS_PER_CATEGORY:
                return category
        return None

    async def _get_or_create_category(self, cls: ClassChannel) -> CategoryChannel:
        """
        Gets or creates a new category channel for a class channel.
        If a new category is created, the passed ClassChannel reference
        is updated, but the update is not pushed to the database.
        """
        category_name = cls.intended_category()
        for category in self.bot.guild.categories:
            if cls.category_id == category.id:
                return category
        new_category = await self.bot.guild.create_category(name=category_name)
        cls.category_id = new_category.id
        return new_category

    async def _get_or_create_role(self, cls: ClassChannel) -> discord.Role:
        """
        Gets or creates a new role for a class channel.
        If a new role is created, the passed ClassChannel reference
        is updated, but the update is not pushed to the database.
        """
        if not (role := self.bot.guild.get_role(cls.class_role_id)):
            new_role = await self.bot.guild.create_role(
                name=cls.class_code(),
                mentionable=True
            )
            cls.class_role_id = new_role.id
            return new_role
        return role

    async def load_service(self):
        self.semester = await self.repo.get_current_semester()
        log.info(f'Loaded semester: {self.semester}')
        if self.semester:
            self.bot.scheduler.schedule_at(
                self.on_semester_archive(self.bot.guild, self.semester),
                time=self.semester.end_date()
            )
        else:
            next_semester = await self.repo.get_next_semester()
            assert next_semester is not None
            self.bot.scheduler.schedule_at(self._refresh_semester(), time=next_semester.start_date())
