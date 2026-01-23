from dataclasses import dataclass, field
from typing import List, Dict, TYPE_CHECKING
from core.table import Table
from enum import Enum

if TYPE_CHECKING:
    from core.player import Player


class RoundState(str, Enum):
    PREPARATION = "preparation"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"


@dataclass
class Round:
    """
    Représente un round d'un tournoi.
    """
    number: int
    tables: list[Table] = field(default_factory=list)
    state: RoundState = RoundState.PREPARATION

    def start(self) -> bool:
        if self.state != RoundState.PREPARATION:
            return False
        self.state = RoundState.IN_PROGRESS
        return True

    def finish(self) -> bool:
        if self.state != RoundState.IN_PROGRESS:
            return False
        self.state = RoundState.FINISHED
        return True

    def to_dict(self) -> Dict:
        return {
            "number": self.number,
            "state": self.state.value,
            "tables": [t.to_dict() for t in self.tables],
        }

    @classmethod
    def from_dict(cls, data: Dict, players_by_id: dict[int, "Player"]) -> "Round":
        tables = [
            Table.from_dict(t, players_by_id)
            for t in data.get("tables", [])
        ]
        return cls(
            number=data["number"],
            state=RoundState(data.get("state", "preparation")),
            tables=tables,
        )