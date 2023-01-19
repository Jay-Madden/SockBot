from dataclasses import dataclass
from datetime import datetime

from bot.utils.helpers import strtodt


@dataclass
class ClassGuild:
    guild_id: int
    notifications_channel_id: int | None = None


@dataclass
class ClassSemester:
    semester_id: str
    semester_name: str
    semester_start: str
    semester_end: str

    def start_date(self) -> datetime:
        return strtodt(self.semester_start)

    def end_date(self) -> datetime:
        return strtodt(self.semester_end)


@dataclass
class ClassChannel:
    channel_id: int
    semester_id: str
    category_id: int
    class_role_id: int
    class_prefix: str
    class_number: int
    post_message_id: int
    class_professor: str
    class_name: str
    class_archived: bool = False
    class_description: str | None = None

    @property
    def class_professor(self) -> str:
        return self.class_professor

    @class_professor.setter
    def class_professor(self, value: str) -> None:
        if len(split := value.split(' ')) > 1:
            self.class_professor = split[-1].title()
        else:
            self.class_professor = value.title()

    @property
    def class_name(self) -> str:
        return self.class_name

    @class_name.setter
    def class_name(self, value: str) -> None:
        self.class_name = value.title()

    def class_code(self) -> str:
        return f'{self.class_prefix}-{self.class_number}'

    def full_title(self) -> str:
        return f'{self.class_code()}: {self.class_name}'

    def channel_name(self) -> str:
        return f'{self.class_code().lower()}-{self.class_professor.lower()}'

    def intended_category(self) -> str:
        level = (self.class_number // 1000) * 1000
        return f'{self.class_prefix} {level} LEVELS'


@dataclass
class ClassPin:
    pin_message_id: int
    original_post_message_id: int
    channel_id: int
    pin_owner: int
    pin_requester: int
    pin_pinned: bool
