from dataclasses import dataclass


@dataclass
class Birthday:
    member_id: int
    month: int
    day: int
    year: int
    last_used: str
    last_congratulated: str
