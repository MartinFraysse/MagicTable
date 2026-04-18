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
    reward_claimed: bool = False
    commander: str = ""

    # Champs Swiss (départage)
    buchholz: float = 0.0      # Somme des scores des adversaires
    sos: float = 0.0           # Strength of Schedule (moyenne des scores adverses)
    had_bye: bool = False      # A reçu un bye dans ce tournoi

    # Drop / forfait
    dropped: bool = False      # Joueur qui a abandonné le tournoi

    # Lien explicite vers le joueur permanent (None = joueur anonyme du tournoi)
    regular_player_id: int | None = None

    def add_score(self, points: int) -> None:
        self.score += points

    def add_robustness(self, value: int) -> None:
        self.robustness += value