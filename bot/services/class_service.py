import logging

from bot.data.class_repository import ClassRepository, strtodt
from bot.errors import NoSemesterError
from bot.messaging.events import Events
from bot.models.class_models import ClassSemester
from bot.services.base_service import BaseService

log = logging.getLogger(__name__)


class ClassService(BaseService):

    def __init__(self, *, bot):
        super().__init__(bot)
        self.repo = ClassRepository()
        self.semester: ClassSemester | None = None

    @BaseService.Listener(Events.on_class_create)
    async def on_class_create(self):
        if not self.semester:
            raise NoSemesterError()

    @BaseService.Listener(Events.on_semester_archive)
    async def on_semester_archive(self):
        pass

    async def _refresh_semester(self):
        self.semester = self.repo.get_current_semester()

    async def load_service(self):
        self.semester = await self.repo.get_current_semester()
        if self.semester:
            start_date = strtodt(self.semester.semester_start)
            end_date = strtodt(self.semester.semester_end)
            self.bot.scheduler.schedule_at(self._refresh_semester(), time=start_date)
            self.bot.scheduler.schedule_at(self.on_semester_archive(), time=end_date)
