"""
Système de ligue — regroupe plusieurs tournois archivés et calcule un classement cumulé.

Barème par défaut :
  1er : 10 pts  |  2e : 7 pts  |  3e : 5 pts  |  4e : 3 pts
  Autres : participation_pts (défaut : 1 pt)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.tournament import Tournament


# ── Barème par défaut ────────────────────────────────────────────────────────

DEFAULT_SCORING: dict[int, int] = {1: 12, 2: 9, 3: 7, 4: 5, 5: 3, 6: 3, 7: 2, 8: 2}
DEFAULT_PARTICIPATION_PTS: int = 1


# ── Modèle ───────────────────────────────────────────────────────────────────

@dataclass
class League:
    """Une ligue regroupe N tournois archivés sous un barème commun."""
    id: int
    name: str
    format: str          # correspond au format des tournois (ex. "👑 Commander")
    season: str          # ex. "2026", "Saison 1"
    tournament_ids: list[int] = field(default_factory=list)
    scoring: dict[int, int] = field(default_factory=lambda: dict(DEFAULT_SCORING))
    participation_pts: int = DEFAULT_PARTICIPATION_PTS

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "format": self.format,
            "season": self.season,
            "tournament_ids": self.tournament_ids,
            # JSON force les clés en str → on les stocke en str
            "scoring": {str(k): v for k, v in self.scoring.items()},
            "participation_pts": self.participation_pts,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "League":
        return cls(
            id=data["id"],
            name=data["name"],
            format=data["format"],
            season=data.get("season", ""),
            tournament_ids=data.get("tournament_ids", []),
            scoring={int(k): int(v) for k, v in data.get("scoring", {}).items()},
            participation_pts=data.get("participation_pts", DEFAULT_PARTICIPATION_PTS),
        )


@dataclass
class LeagueStandingEntry:
    rank: int
    player_name: str
    total_points: int
    tournaments_played: int
    best_result: int        # meilleur classement obtenu (1 = 1er)


# ── Calcul ───────────────────────────────────────────────────────────────────

def compute_league_standings(
    league: League,
    tournaments: list["Tournament"],
) -> list[LeagueStandingEntry]:
    """
    Calcule le classement de ligue en parcourant tous les tournois archivés liés.

    Chaque tournoi contribue des points selon le barème de la ligue.
    Tri : points DESC → meilleur résultat ASC → nom ASC.
    """
    league_ids = set(league.tournament_ids)
    relevant = [t for t in tournaments if t.id in league_ids and t.archived]

    # player_name → [total_pts, tournaments_played, best_result]
    stats: dict[str, list[int]] = {}

    for tournament in relevant:
        ranking = get_tournament_final_ranking(tournament)
        for rank, name in enumerate(ranking, 1):
            if name not in stats:
                stats[name] = [0, 0, rank]
            pts = league.scoring.get(rank, league.participation_pts)
            stats[name][0] += pts
            stats[name][1] += 1
            stats[name][2] = min(stats[name][2], rank)

    sorted_stats = sorted(
        stats.items(),
        key=lambda x: (-x[1][0], x[1][2], x[0]),  # pts DESC, best ASC, nom ASC
    )

    return [
        LeagueStandingEntry(
            rank=i + 1,
            player_name=name,
            total_points=s[0],
            tournaments_played=s[1],
            best_result=s[2],
        )
        for i, (name, s) in enumerate(sorted_stats)
    ]


def get_tournament_final_ranking(tournament: "Tournament") -> list[str]:
    """
    Retourne les noms des joueurs dans leur ordre de classement final (1er en tête).
    Prend en compte le bracket si présent.
    """
    from core.standings import build_standings
    from core.bracket import get_bracket_final_ranking

    if not tournament.players:
        return []

    players_by_id = {p.id: p for p in tournament.players}

    if tournament.is_1v1_format():
        standings = build_standings(tournament)
        swiss_ordered = [
            players_by_id[e.player_id]
            for e in standings
            if e.player_id in players_by_id
        ]
    else:
        swiss_ordered = sorted(
            tournament.players,
            key=lambda p: (-p.score, -p.robustness, p.name),
        )

    if tournament.bracket:
        swiss_ids = [p.id for p in swiss_ordered]
        final_ids = get_bracket_final_ranking(tournament.bracket, swiss_ids)
        ranked = [players_by_id[pid] for pid in final_ids if pid in players_by_id]
    else:
        ranked = swiss_ordered

    return [p.name for p in ranked]


# ── Utils ────────────────────────────────────────────────────────────────────

def get_player_league_history(
    league: "League",
    player_name: str,
    tournaments: list["Tournament"],
) -> list[tuple]:
    """
    Retourne l'historique d'un joueur dans une ligue :
    liste de (tournament, rank, points) triée par date décroissante.
    """
    league_ids = set(league.tournament_ids)
    relevant = [t for t in tournaments if t.id in league_ids and t.archived]

    history = []
    for t in relevant:
        ranking = get_tournament_final_ranking(t)
        if player_name in ranking:
            rank = ranking.index(player_name) + 1
            pts = league.scoring.get(rank, league.participation_pts)
            history.append((t, rank, pts))

    history.sort(key=lambda x: x[0].date, reverse=True)
    return history


def next_free_league_id(leagues: list[League]) -> int:
    if not leagues:
        return 0
    return max(lg.id for lg in leagues) + 1
