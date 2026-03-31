from dataclasses import dataclass, field
from typing import List, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from core.player import Player


@dataclass
class Table:
    """
    Représente une table de jeu dans un round.
    """
    number: int
    players: list["Player"]

    finished: bool = False
    results: dict[int, int] = field(default_factory=dict)
    # results : player_id -> position (1, 2, 3, 4)
    game_scores: dict[int, int] = field(default_factory=dict)
    # game_scores : player_id -> games gagnées (BO3 : 0, 1 ou 2)

    def player_count(self) -> int:
        return len(self.players)

    def to_dict(self) -> Dict:
        return {
            "number": self.number,
            "player_ids": [p.id for p in self.players],
            "finished": self.finished,
            "results": self.results,
            "game_scores": self.game_scores,
        }

    @classmethod
    def from_dict(cls, data: Dict, players_by_id: dict[int, "Player"]) -> "Table":
        table_players = [
            players_by_id[pid]
            for pid in data.get("player_ids", [])
            if pid in players_by_id
        ]
        table = cls(
            number=data["number"],
            players=table_players,
            finished=data.get("finished", False),
            results={int(k): v for k, v in data.get("results", {}).items()},
            game_scores={int(k): v for k, v in data.get("game_scores", {}).items()},
        )
        return table
