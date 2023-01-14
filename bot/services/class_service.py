import logging

from discord import CategoryChannel

from bot.bot_secrets import BotSecrets
from bot.data.class_repository import ClassRepository, strtodt
from bot.errors import NoSemesterError
from bot.messaging.events import Events
from bot.models.class_models import ClassSemester
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
    async def on_semester_archive(self, semester: ClassSemester):
        if not self.semester:
            log.error('on_semester_archive called while current semester is None')
            return
        category_ids = BotSecrets.class_archive_category_ids
        channels = self.repo.get_semester_classes(semester)

    async def _refresh_semester(self):
        self.semester = self.repo.get_current_semester()
        if not self.semester:
            log.error('Refreshing the current semester resulted in None.')
            return
        # TODO: Announce that the semester is currently in session?

    def _available_archive_slots(self) -> dict[CategoryChannel, int]:
        categories = dict()
        archive_categories = BotSecrets.class_archive_category_ids
        for category in self.bot.guild.categories:
            if category.id in archive_categories:
                categories[category] = MAX_CHANNELS_PER_CATEGORY - len(category.channels)
        return categories

    async def load_service(self):
        self.semester = await self.repo.get_current_semester()
        if self.semester:
            start_date = strtodt(self.semester.semester_start)
            end_date = strtodt(self.semester.semester_end)
            self.bot.scheduler.schedule_at(await self._refresh_semester(), time=start_date)
            self.bot.scheduler.schedule_at(await self.on_semester_archive(self.semester), time=end_date)
