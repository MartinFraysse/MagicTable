"""
Calcul des standings MTG officiels pour les formats 1v1.

Implémente les règles officielles Magic: The Gathering pour le classement suisse :
- Match Points : Win=3, Draw=1, Loss=0
- Tiebreakers (dans l'ordre) :
    1. OMW% (Opponent Match Win Percentage) avec floor 0.33
    2. GW%  (Game Win Percentage) — placeholder 0.0 (games non trackés)
    3. OGW% (Opponent Game Win Percentage) — placeholder 0.0
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.tournament import Tournament


@dataclass
class StandingEntry:
    """Entrée de classement pour un joueur."""
    player_id: int
    player_name: str
    match_points: int = 0       # 3 * wins + 1 * draws
    wins: int = 0
    draws: int = 0
    losses: int = 0
    matches_played: int = 0
    mw_pct: float = 0.0        # Match Win % = match_points / (3 * matches_played)
    omw_pct: float = 0.0       # Opponent Match Win % (floor 0.33 par adversaire)
    gw_pct: float = 0.0        # Game Win % (placeholder — games non trackés)
    ogw_pct: float = 0.0       # Opponent Game Win % (placeholder)


def build_standings(tournament: Tournament) -> list[StandingEntry]:
    """
    Calcule les standings complets d'un tournoi 1v1 à partir des résultats bruts.

    Lit tous les rounds/tables/results du tournoi et produit un classement trié
    selon les règles MTG officielles :
        match_points DESC → OMW% DESC → GW% DESC → OGW% DESC → name ASC

    Args:
        tournament: Le tournoi dont on calcule les standings.

    Returns:
        Liste de StandingEntry triée du premier au dernier.
    """
    # ---------------------------------------------------------------
    # Phase 1 : collecter wins / draws / losses et adversaires
    # ---------------------------------------------------------------
    stats: dict[int, _PlayerStats] = {}

    for player in tournament.players:
        stats[player.id] = _PlayerStats(
            player_id=player.id,
            player_name=player.name,
        )

    for rnd in tournament.rounds:
        if not rnd.tables:
            continue

        for table in rnd.tables:
            if not table.finished:
                continue

            players = table.players

            # --- Bye (1 seul joueur) : victoire automatique, pas d'adversaire ---
            if len(players) == 1:
                pid = players[0].id
                if pid in stats:
                    stats[pid].wins += 1
                    stats[pid].matches_played += 1
                    # Pas d'adversaire → pas ajouté à opponents
                continue

            # --- Match 1v1 (2 joueurs) ---
            if len(players) == 2:
                p1, p2 = players
                pos1 = table.results.get(p1.id)
                pos2 = table.results.get(p2.id)

                # Résultat manquant → ne pas compter
                if pos1 is None or pos2 is None:
                    continue

                _record_1v1_result(stats, p1.id, p2.id, pos1, pos2)
                continue

    # ---------------------------------------------------------------
    # Phase 2 : calculer MW% pour chaque joueur
    # ---------------------------------------------------------------
    for s in stats.values():
        s.match_points = 3 * s.wins + 1 * s.draws
        if s.matches_played > 0:
            s.mw_pct = s.match_points / (3 * s.matches_played)
        else:
            s.mw_pct = 0.0

    # ---------------------------------------------------------------
    # Phase 3 : calculer OMW% (floor 0.33 par adversaire)
    # ---------------------------------------------------------------
    #
    # Pour chaque joueur J, on prend tous ses adversaires (hors bye).
    # Pour chaque adversaire A :
    #     contrib = max(A.mw_pct, 0.33)
    #
    # OMW%(J) = moyenne des contrib.
    # Si aucun adversaire → 0.0
    #
    # Le floor à 0.33 évite qu'un adversaire à 0% tire trop le score
    # vers le bas (équivalent à un joueur qui gagnerait 1 match sur 3).
    # ---------------------------------------------------------------
    for s in stats.values():
        if not s.opponents:
            s.omw_pct = 0.0
            continue

        total = 0.0
        count = 0
        for opp_id in s.opponents:
            opp = stats.get(opp_id)
            if opp is None:
                continue
            total += max(opp.mw_pct, 0.33)
            count += 1

        s.omw_pct = total / count if count > 0 else 0.0

    # ---------------------------------------------------------------
    # Phase 4 : GW% et OGW% — placeholders (games non trackés)
    # ---------------------------------------------------------------
    # GW% = games_won / games_played — non disponible dans le modèle actuel.
    # OGW% = moyenne des GW% adverses avec floor 0.33 — idem.
    # Les deux restent à 0.0 et pourront être implémentés si le modèle
    # est étendu pour tracker les résultats par game (ex: 2-1, 2-0).

    # ---------------------------------------------------------------
    # Phase 5 : construire les StandingEntry et trier
    # ---------------------------------------------------------------
    entries: list[StandingEntry] = []
    for s in stats.values():
        entries.append(StandingEntry(
            player_id=s.player_id,
            player_name=s.player_name,
            match_points=s.match_points,
            wins=s.wins,
            draws=s.draws,
            losses=s.losses,
            matches_played=s.matches_played,
            mw_pct=s.mw_pct,
            omw_pct=s.omw_pct,
            gw_pct=0.0,
            ogw_pct=0.0,
        ))

    # Tri officiel MTG :
    #   match_points DESC → OMW% DESC → GW% DESC → OGW% DESC → name ASC
    entries.sort(key=lambda e: (
        -e.match_points,
        -e.omw_pct,
        -e.gw_pct,
        -e.ogw_pct,
        e.player_name,
    ))

    return entries


# =====================================================================
# Helpers internes
# =====================================================================

@dataclass
class _PlayerStats:
    """Accumulateur interne pour le calcul des standings."""
    player_id: int
    player_name: str
    wins: int = 0
    draws: int = 0
    losses: int = 0
    matches_played: int = 0
    match_points: int = 0
    mw_pct: float = 0.0
    omw_pct: float = 0.0
    opponents: list[int] = field(default_factory=list)


def _record_1v1_result(
    stats: dict[int, _PlayerStats],
    p1_id: int,
    p2_id: int,
    pos1: int,
    pos2: int,
) -> None:
    """
    Enregistre le résultat d'un match 1v1 dans les stats.

    - Position plus basse = meilleur (1 = gagnant).
    - Positions identiques = draw (1 pt chacun).
    """
    s1 = stats.get(p1_id)
    s2 = stats.get(p2_id)
    if s1 is None or s2 is None:
        return

    s1.matches_played += 1
    s2.matches_played += 1

    # Enregistrer l'adversaire (pour OMW%)
    s1.opponents.append(p2_id)
    s2.opponents.append(p1_id)

    if pos1 < pos2:
        # p1 gagne
        s1.wins += 1
        s2.losses += 1
    elif pos2 < pos1:
        # p2 gagne
        s2.wins += 1
        s1.losses += 1
    else:
        # Draw (positions identiques)
        s1.draws += 1
        s2.draws += 1
