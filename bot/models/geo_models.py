from dataclasses import dataclass


@dataclass
class GeoguessrLeaderboard:
    id: int
    user_id: int
    score: int
