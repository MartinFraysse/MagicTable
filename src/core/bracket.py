"""
Modele de donnees pour la phase finale (bracket d'elimination).

Gere les formats :
- Quart de Finale (top 8) : 3 rounds (quart → demi → finale)
- Demi-Finale (top 4) : 2 rounds (demi → finale)
- Finale (top 2) : 1 round (finale)

Pairings par seed :
- Quart : 1v8, 4v5, 2v7, 3v6
- Demi  : 1v4, 2v3
- Finale: 1v2
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict


class BracketType(str, Enum):
    FINAL = "final"
    DEMI_FINALE = "demi"
    QUART_DE_FINALE = "quart"


class BracketRoundName(str, Enum):
    QUART = "quart"
    DEMI = "demi"
    FINAL = "final"


# Ordre de progression des rounds par type de bracket
_ROUND_ORDER: dict[BracketType, list[BracketRoundName]] = {
    BracketType.QUART_DE_FINALE: [BracketRoundName.QUART, BracketRoundName.DEMI, BracketRoundName.FINAL],
    BracketType.DEMI_FINALE: [BracketRoundName.DEMI, BracketRoundName.FINAL],
    BracketType.FINAL: [BracketRoundName.FINAL],
}


@dataclass
class BracketMatch:
    """Un match dans le bracket d'elimination."""
    match_id: int
    round_name: BracketRoundName
    position: int                          # Position dans le round (0-based)
    player1_id: int | None = None
    player2_id: int | None = None
    winner_id: int | None = None
    finished: bool = False
    next_match_id: int | None = None       # Match ou le gagnant est envoye

    def to_dict(self) -> Dict:
        return {
            "match_id": self.match_id,
            "round_name": self.round_name.value,
            "position": self.position,
            "player1_id": self.player1_id,
            "player2_id": self.player2_id,
            "winner_id": self.winner_id,
            "finished": self.finished,
            "next_match_id": self.next_match_id,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> BracketMatch:
        return cls(
            match_id=data["match_id"],
            round_name=BracketRoundName(data["round_name"]),
            position=data["position"],
            player1_id=data.get("player1_id"),
            player2_id=data.get("player2_id"),
            winner_id=data.get("winner_id"),
            finished=data.get("finished", False),
            next_match_id=data.get("next_match_id"),
        )


@dataclass
class Bracket:
    """Phase finale d'elimination."""
    bracket_type: BracketType
    matches: list[BracketMatch] = field(default_factory=list)
    finished: bool = False

    def current_round_name(self) -> BracketRoundName | None:
        """Retourne le nom du round actif (premier round non termine)."""
        for round_name in _ROUND_ORDER[self.bracket_type]:
            round_matches = self.get_matches_for_round(round_name)
            if round_matches and not all(m.finished for m in round_matches):
                return round_name
        return None

    def get_matches_for_round(self, round_name: BracketRoundName) -> list[BracketMatch]:
        return [m for m in self.matches if m.round_name == round_name]

    def all_current_round_finished(self) -> bool:
        current = self.current_round_name()
        if current is None:
            return True
        return all(m.finished for m in self.get_matches_for_round(current))

    def record_result(self, match_id: int, winner_id: int) -> None:
        """Enregistre le resultat et propage le gagnant au match suivant."""
        match = next((m for m in self.matches if m.match_id == match_id), None)
        if not match:
            return

        match.winner_id = winner_id
        match.finished = True

        # Propager le gagnant vers le match suivant
        if match.next_match_id is not None:
            next_match = next(
                (m for m in self.matches if m.match_id == match.next_match_id),
                None,
            )
            if next_match:
                if next_match.player1_id is None:
                    next_match.player1_id = winner_id
                else:
                    next_match.player2_id = winner_id

        # Verifier si le bracket est termine
        final_matches = self.get_matches_for_round(BracketRoundName.FINAL)
        if final_matches and all(m.finished for m in final_matches):
            self.finished = True

    def get_round_order(self) -> list[BracketRoundName]:
        return _ROUND_ORDER[self.bracket_type]

    def to_dict(self) -> Dict:
        return {
            "bracket_type": self.bracket_type.value,
            "matches": [m.to_dict() for m in self.matches],
            "finished": self.finished,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> Bracket:
        return cls(
            bracket_type=BracketType(data["bracket_type"]),
            matches=[BracketMatch.from_dict(m) for m in data.get("matches", [])],
            finished=data.get("finished", False),
        )


def create_bracket_matches(
    bracket_type: BracketType,
    seeded_player_ids: list[int],
) -> list[BracketMatch]:
    """
    Cree les matches du bracket a partir des IDs de joueurs tries par seed.

    seeded_player_ids : liste ordonnee [1er, 2eme, ..., Neme]
    """
    matches: list[BracketMatch] = []

    if bracket_type == BracketType.QUART_DE_FINALE:
        # Quart: 1v8, 4v5, 2v7, 3v6
        # Organise pour que les meilleurs seeds se rencontrent en finale
        quart_pairings = [(0, 7), (3, 4), (1, 6), (2, 5)]
        for i, (a, b) in enumerate(quart_pairings):
            matches.append(BracketMatch(
                match_id=i,
                round_name=BracketRoundName.QUART,
                position=i,
                player1_id=seeded_player_ids[a],
                player2_id=seeded_player_ids[b],
                next_match_id=4 + i // 2,
            ))
        # Demi-finales (match_id 4, 5)
        for i in range(2):
            matches.append(BracketMatch(
                match_id=4 + i,
                round_name=BracketRoundName.DEMI,
                position=i,
                next_match_id=6,
            ))
        # Finale (match_id 6)
        matches.append(BracketMatch(
            match_id=6,
            round_name=BracketRoundName.FINAL,
            position=0,
        ))

    elif bracket_type == BracketType.DEMI_FINALE:
        # Demi: 1v4, 2v3
        demi_pairings = [(0, 3), (1, 2)]
        for i, (a, b) in enumerate(demi_pairings):
            matches.append(BracketMatch(
                match_id=i,
                round_name=BracketRoundName.DEMI,
                position=i,
                player1_id=seeded_player_ids[a],
                player2_id=seeded_player_ids[b],
                next_match_id=2,
            ))
        # Finale (match_id 2)
        matches.append(BracketMatch(
            match_id=2,
            round_name=BracketRoundName.FINAL,
            position=0,
        ))

    elif bracket_type == BracketType.FINAL:
        # Finale: 1v2
        matches.append(BracketMatch(
            match_id=0,
            round_name=BracketRoundName.FINAL,
            position=0,
            player1_id=seeded_player_ids[0],
            player2_id=seeded_player_ids[1],
        ))

    return matches
