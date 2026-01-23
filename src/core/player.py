from dataclasses import dataclass


@dataclass
class Player:
    """
    Classe métier représentant un joueur.
    """

    id: int
    name: str
    score: int = 0
    robustness: int = 0

    def add_score(self, points: int) -> None:
        self.score += points

    def add_robustness(self, value: int) -> None:
        self.robustness += value