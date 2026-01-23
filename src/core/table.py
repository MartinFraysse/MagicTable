from dataclasses import dataclass, field
from typing import List, Dict
from core.player import Player


@dataclass
class Table:
    """
    Représente une table de jeu dans un round.
    """
    number: int
    players: list[Player]

    finished: bool = False
    results: dict[int, int] = field(default_factory=dict)
    # results : player_id -> position (1, 2, 3, 4)

    def player_count(self) -> int:
        return len(self.players)
