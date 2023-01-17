from dataclasses import dataclass
from datetime import datetime

from bot.utils.helpers import strtodt


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
    class_archived: bool
    class_description: str | None

    def class_code(self) -> str:
        return f'{self.class_prefix}-{self.class_number}'

    def full_title(self) -> str:
        return f'{self.class_code()}: {self.class_name}'


@dataclass
class ClassPin:
    pin_message_id: int
    original_post_message_id: int
    channel_id: int
    pin_owner: int
    pin_requester: int
    pin_pinned: bool
