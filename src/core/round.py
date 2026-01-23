from dataclasses import dataclass, field
from typing import List
from core.table import Table
from enum import Enum

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
        return True30062