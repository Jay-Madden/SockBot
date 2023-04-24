from dataclasses import dataclass
from datetime import datetime

from bot.utils.helpers import strtodt


@dataclass
class ClassSemester:
    semester_id: str
    semester_name: str
    semester_start: str
    semester_end: str

    @property
    def start_date(self) -> datetime:
        return strtodt(self.semester_start)

    @property
    def end_date(self) -> datetime:
        return strtodt(self.semester_end)


@dataclass
class ClassChannelScaffold:
    class_prefix: str
    class_number: int
    class_professor: str
    class_name: str

    @property
    def class_code(self) -> str:
        return f'{self.class_prefix}-{self.class_number}'

    @property
    def full_title(self) -> str:
        return f'{self.class_code}: {self.class_name}'

    @property
    def channel_name(self) -> str:
        return f'{self.class_code.lower()}-{self.class_professor.lower()}'

    @property
    def intended_category(self) -> str:
        level = (self.class_number // 1000) * 1000
        return f'{self.class_prefix} {level} LEVELS'


@dataclass
class ClassChannel(ClassChannelScaffold):
    channel_id: int
    semester_id: str
    category_id: int
    class_role_id: int
    class_ta_role_id: int | None
    post_message_id: int | None
    class_archived: bool = False


@dataclass
class ClassPin:
    sockbot_message_id: int
    user_message_id: int
    channel_id: int
    pin_owner: int
    pin_requester: int
    pin_pinned: bool = False


@dataclass
class ClassTA:
    channel_id: int
    ta_user_id: int
    ta_display_tag: bool
    ta_details: str | None
