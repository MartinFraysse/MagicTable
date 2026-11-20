"""
Système d'appariement Swiss 1v1 — couplage optimal (algorithme de blossom).

Chaque round est le meilleur appariement possible selon ces priorités
(de la plus forte à la plus faible) :

  1. Pas de second bye si un autre joueur peut le recevoir
  2. Pas de rematch si une alternative existe
  3. Bye attribué au joueur le moins bien classé (en points)
  4. Écarts de points minimaux entre adversaires — pénalité quadratique :
     on préfère deux petits « pair-downs » (9-6 et 6-3) à un gros (9-0)
  5. Hasard entre appariements équivalents (round 1 aléatoire, joueurs à
     égalité de points appariés aléatoirement, comme le prévoit la MTR)

Le problème est résolu exactement par un couplage parfait de poids minimal
(networkx.max_weight_matching) : pas d'heuristique, pas de limite d'itérations.
Si le nombre de joueurs est impair, un nœud « BYE » est ajouté au graphe.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from networkx import Graph
from networkx.algorithms.matching import max_weight_matching

if TYPE_CHECKING:
    from core.player import Player


@dataclass
class SwissPairingResult:
    """Résultat d'un appariement Swiss."""
    pairings: list[tuple["Player", "Player"]]
    bye_player: "Player | None"
    had_rematch: bool = False


def compute_recommended_rounds(player_count: int) -> int:
    """
    Calcule le nombre de rounds recommandé pour un tournoi Swiss.
    Formule : ceil(log2(n))

    Exemples :
    - 4-8 joueurs  → 3 rounds
    - 9-16 joueurs → 4 rounds
    - 17-32 joueurs → 5 rounds
    """
    if player_count < 2:
        return 0
    return math.ceil(math.log2(player_count))


# ── Coûts (lexicographiques) ─────────────────────────────────────────────────
# Chaque niveau doit dépasser la somme maximale possible des niveaux inférieurs.
# Avec des écarts de points ≤ 3 × 50 rounds et ≤ 256 joueurs, les marges sont larges.
_JITTER = 1_000                 # hasard : départage entre appariements équivalents
_GAP = 10 ** 6                  # × écart² de points (≤ 150² × 128 paires ≈ 2,9e9)
_BYE_POINTS = 10 ** 13          # × points du joueur qui reçoit le bye
_REMATCH = 10 ** 17             # par rematch
_REPEAT_BYE = 10 ** 21          # second bye
_BASE = 10 ** 24                # poids de base (maximisation → coût négatif)

_BYE_NODE = "__BYE__"


def generate_swiss_pairings(
    players: list["Player"],
    opponents_map: dict[int, set[int]],
    bye_history: set[int],
    standings_order: list[int] | None = None,
    rng: random.Random | None = None,
) -> SwissPairingResult:
    """
    Génère les appariements Swiss d'un round pour les joueurs actifs.

    players       : joueurs actifs (non droppés), avec `score` = points de match à jour
    opponents_map : player_id → ids des adversaires déjà rencontrés
    bye_history   : ids des joueurs ayant déjà reçu un bye
    standings_order : ordre du classement (ids) — ne sert qu'à l'affichage des tables
                      (meilleurs joueurs aux premières tables)
    rng           : générateur aléatoire (injectable pour les tests)
    """
    rng = rng or random
    if not players:
        return SwissPairingResult(pairings=[], bye_player=None)

    graph = Graph()
    by_id = {p.id: p for p in players}
    order = list(players)
    rng.shuffle(order)  # l'ordre d'insertion influence aussi le départage

    def add_edge(u, v, cost: int) -> None:
        jitter = rng.randrange(_JITTER // max(1, len(players)))
        graph.add_edge(u, v, weight=_BASE - cost - jitter)

    for i, a in enumerate(order):
        for b in order[i + 1:]:
            cost = _GAP * (a.score - b.score) ** 2
            if b.id in opponents_map.get(a.id, set()):
                cost += _REMATCH
            add_edge(a.id, b.id, cost)

    if len(players) % 2 == 1:
        for p in order:
            cost = _BYE_POINTS * max(p.score, 0)
            if p.id in bye_history:
                cost += _REPEAT_BYE
            add_edge(p.id, _BYE_NODE, cost)

    matching = max_weight_matching(graph, maxcardinality=True)

    bye_player: "Player | None" = None
    pairings: list[tuple["Player", "Player"]] = []
    for u, v in matching:
        if _BYE_NODE in (u, v):
            bye_player = by_id[v if u == _BYE_NODE else u]
            continue
        a, b = by_id[u], by_id[v]
        pairings.append((a, b))

    # Tables numérotées du haut vers le bas du classement
    rank = {pid: i for i, pid in enumerate(standings_order or [])}

    def table_key(pair: tuple["Player", "Player"]) -> tuple:
        a, b = pair
        return (-max(a.score, b.score), min(rank.get(a.id, len(rank)), rank.get(b.id, len(rank))))

    oriented = []
    for a, b in sorted(pairings, key=table_key):
        # Le mieux classé en premier dans la table
        if rank.get(b.id, len(rank)) < rank.get(a.id, len(rank)):
            a, b = b, a
        oriented.append((a, b))

    had_rematch = any(b.id in opponents_map.get(a.id, set()) for a, b in oriented)
    return SwissPairingResult(pairings=oriented, bye_player=bye_player, had_rematch=had_rematch)
