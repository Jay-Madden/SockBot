from dataclasses import dataclass


@dataclass
class ClassSemester:
    semester_id: str
    semester_name: str
    semester_start: str
    semester_end: str


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


@dataclass
class ClassPin:
    pin_message_id: int
    original_post_message_id: int
    channel_id: int
    pin_owner: int
    pin_pinned: bool
