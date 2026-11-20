"""
Classements d'un tournoi : barème Commander, ordre Swiss/standard et classement final.

Point d'entrée unique utilisé par le dashboard, l'historique, les stats, les ligues
et l'export PDF.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from core.bracket import get_bracket_final_ranking
from core.standings import build_standings

if TYPE_CHECKING:
    from core.player import Player
    from core.tournament import Tournament


# Commander multijoueur : 1er = 3 pts, 2e = 2 pts, 3e et au-delà = 1 pt
COMMANDER_POINTS: dict[int, int] = {1: 3, 2: 2, 3: 1, 4: 1}


def commander_points(position: int) -> int:
    """Points Commander pour une position à table."""
    return COMMANDER_POINTS.get(position, 1)


def commander_sort_key(player: "Player") -> tuple:
    """Clé de tri Commander : score DESC → robustesse DESC → nom ASC."""
    return (-player.score, -player.robustness, player.name)


def swiss_order(tournament: "Tournament") -> list["Player"]:
    """
    Classement des rondes (hors bracket) :
    - 1v1 : standings MTG officiels (match points → OMW% → GW% → OGW%) ;
    - Commander : score → robustesse → nom.
    """
    if tournament.is_1v1_format():
        players_by_id = {p.id: p for p in tournament.players}
        return [
            players_by_id[e.player_id]
            for e in build_standings(tournament)
            if e.player_id in players_by_id
        ]
    return sorted(tournament.players, key=commander_sort_key)


def final_ranking(tournament: "Tournament") -> list["Player"]:
    """
    Classement final du tournoi (1er en tête).
    Si un bracket existe (même partiel), son résultat prime sur le classement des rondes,
    qui sert de départage à stade égal.
    """
    ordered = swiss_order(tournament)
    if not tournament.bracket:
        return ordered

    players_by_id = {p.id: p for p in tournament.players}
    final_ids = get_bracket_final_ranking(tournament.bracket, [p.id for p in ordered])
    return [players_by_id[pid] for pid in final_ids if pid in players_by_id]
