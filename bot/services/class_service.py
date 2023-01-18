import logging

import discord
from discord import CategoryChannel

from bot.bot_secrets import BotSecrets
from bot.data.class_repository import ClassRepository, strtodt
from bot.errors import NoSemesterError
from bot.messaging.events import Events
from bot.models.class_models import ClassSemester, ClassChannel
from bot.services.base_service import BaseService
from bot.sock_bot import SockBot

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
    async def on_semester_archive(self, inter: discord.Interaction | None, semester: ClassSemester):
        if not self.semester:
            log.error('on_semester_archive called while current semester is None')
            return
        category_ids = BotSecrets.class_archive_category_ids
        channels = await self.repo.get_semester_classes(semester)

    async def _refresh_semester(self):
        self.semester = await self.repo.get_current_semester()
        if not self.semester:
            log.error('Refreshing the current semester resulted in None.')
            return
        # TODO: Announce that the semester is currently in session?

    def _available_archive_slots(self) -> dict[CategoryChannel, int]:
        """
        Gets a dictionary of archive category channels and the number of slots available.
        """
        categories = dict()
        archive_categories = BotSecrets.class_archive_category_ids
        for category in self.bot.guild.categories:
            if category.id in archive_categories:
                categories[category] = MAX_CHANNELS_PER_CATEGORY - len(category.channels)
        return categories

    def _get_or_create_category(self, cls: ClassChannel) -> CategoryChannel:
        """
        Gets or creates a new category channel for a class channel.
        If a new category is created, the passed ClassChannel reference
        is NOT updated inside of this method and is not sent to the database.
        """
        category_name = cls.intended_category()
        for category in self.bot.guild.categories:
            if cls.category_id == category.id:
                return category
        return await self.bot.guild.create_category(name=category_name)

    def _get_or_create_role(self, cls: ClassChannel) -> discord.Role:
        """
        Gets or creates a new role for a class channel.
        If a new role is created, the passed ClassChannel reference
        is updated, but t
        """
        if not (role := self.bot.guild.get_role(cls.class_role_id)):
            return await self.bot.guild.create_role(
                name=cls.class_code(),
                mentionable=True
            )
        return role

    async def load_service(self):
        self.semester = await self.repo.get_current_semester()
        log.info(f'Loaded semester: {self.semester}')
        if self.semester:
            self.bot.scheduler.schedule_at(
                await self.on_semester_archive(None, self.semester),
                time=self.semester.end_date()
            )
        else:
            next_semester = await self.repo.get_next_semester()
            assert next_semester is not None
            self.bot.scheduler.schedule_at(await self._refresh_semester(), time=next_semester.start_date())
