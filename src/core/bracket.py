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

    def reset_result(self, match_id: int) -> None:
        """
        Annule le résultat d'un match et propage la réinitialisation
        aux matches suivants en cascade (si le vainqueur avait déjà avancé).
        """
        match = next((m for m in self.matches if m.match_id == match_id), None)
        if not match or not match.finished:
            return

        old_winner_id = match.winner_id
        match.winner_id = None
        match.finished = False
        self.finished = False

        if match.next_match_id is None:
            return

        next_match = next(
            (m for m in self.matches if m.match_id == match.next_match_id), None
        )
        if not next_match:
            return

        # Retirer l'ancien vainqueur du slot correspondant dans le match suivant
        if next_match.player1_id == old_winner_id:
            next_match.player1_id = None
        elif next_match.player2_id == old_winner_id:
            next_match.player2_id = None

        # Cascade : si le match suivant avait déjà un résultat, le réinitialiser aussi
        if next_match.finished:
            self.reset_result(next_match.match_id)

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


def get_bracket_final_ranking(bracket: "Bracket", swiss_seeded_ids: list[int]) -> list[int]:
    """
    Retourne les IDs des joueurs dans l'ordre du classement final.

    Fonctionne avec un bracket terminé OU partiel :
      1. Vainqueur de la finale
      2. Finaliste (ou les deux finalistes à égalité si finale non jouée → départage Swiss)
      3-4. Perdants des demi-finales (départage Swiss)
      5-8. Perdants des quarts de finale (départage Swiss)
      Reste. Joueurs hors bracket (ordre Swiss)

    Pour un bracket partiel : les joueurs encore en lice sont classés après les éliminés
    de leur stade, triés par classement Swiss.

    swiss_seeded_ids : IDs de TOUS les joueurs triés par classement Swiss (meilleur en premier).
    """

    def swiss_rank(pid: int) -> int:
        try:
            return swiss_seeded_ids.index(pid)
        except ValueError:
            return len(swiss_seeded_ids)

    def add_group(group: list[int]):
        """Ajoute un groupe trié par rang Swiss au résultat."""
        sorted_group = sorted(group, key=swiss_rank)
        result.extend(sorted_group)
        already_ranked.update(sorted_group)

    # Tous les participants du bracket
    bracket_pids: set[int] = set()
    for m in bracket.matches:
        if m.player1_id is not None:
            bracket_pids.add(m.player1_id)
        if m.player2_id is not None:
            bracket_pids.add(m.player2_id)

    result: list[int] = []
    already_ranked: set[int] = set()

    # ── Finale ──────────────────────────────────────────────────────────────
    final_matches = bracket.get_matches_for_round(BracketRoundName.FINAL)
    final_match = final_matches[0] if final_matches else None

    if final_match and final_match.finished and final_match.winner_id is not None:
        # Finale jouée : vainqueur puis finaliste
        winner_id = final_match.winner_id
        finalist_id = (
            final_match.player1_id
            if final_match.winner_id == final_match.player2_id
            else final_match.player2_id
        )
        result.append(winner_id)
        already_ranked.add(winner_id)
        if finalist_id and finalist_id not in already_ranked:
            result.append(finalist_id)
            already_ranked.add(finalist_id)
    elif final_match:
        # Finale non jouée : les deux finalistes à égalité → départage Swiss
        finalists = [pid for pid in [final_match.player1_id, final_match.player2_id] if pid is not None]
        add_group(finalists)

    # ── Perdants des demi-finales (rangs 3-4) ────────────────────────────────
    if bracket.bracket_type in (BracketType.QUART_DE_FINALE, BracketType.DEMI_FINALE):
        semi_losers = []
        for m in bracket.get_matches_for_round(BracketRoundName.DEMI):
            if m.finished and m.winner_id is not None:
                loser_id = m.player2_id if m.winner_id == m.player1_id else m.player1_id
                if loser_id is not None and loser_id not in already_ranked:
                    semi_losers.append(loser_id)
        add_group(semi_losers)

    # ── Perdants des quarts de finale (rangs 5-8) ────────────────────────────
    if bracket.bracket_type == BracketType.QUART_DE_FINALE:
        quart_losers = []
        for m in bracket.get_matches_for_round(BracketRoundName.QUART):
            if m.finished and m.winner_id is not None:
                loser_id = m.player2_id if m.winner_id == m.player1_id else m.player1_id
                if loser_id is not None and loser_id not in already_ranked:
                    quart_losers.append(loser_id)
        add_group(quart_losers)

    # ── Joueurs en bracket encore en lice (bracket partiel) ──────────────────
    # Triés par Swiss car on ne peut pas les départager par résultat bracket
    still_active = [pid for pid in bracket_pids if pid not in already_ranked]
    add_group(still_active)

    # ── Joueurs hors bracket (ordre Swiss) ───────────────────────────────────
    result.extend(pid for pid in swiss_seeded_ids if pid not in already_ranked)

    return result


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
