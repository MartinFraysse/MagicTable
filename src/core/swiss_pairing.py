"""
Système d'appariement Swiss 1v1 — backtracking global anti-rematch.

Principes :
- Jamais de rematch si une alternative existe
- Bye intelligent : le candidat dont l'absence permet le meilleur pairing reçoit le bye
- Backtracking global : aucun bracket strict, tous les joueurs sont considérés ensemble
- Automatique et silencieux : aucune alerte levée, le meilleur pairing est toujours retourné
"""
import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

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


def generate_swiss_pairings(
    players: list["Player"],
    opponents_map: dict[int, set[int]],
    bye_history: set[int],
    standings_order: list[int] | None = None,
) -> SwissPairingResult:
    """
    Génère les appariements Swiss pour un round.

    Étapes :
    1. Trier les joueurs par standings (match_points → OMW% → GW% → OGW%)
    2. Si nombre impair : sélectionner le bye intelligemment (voir _select_bye)
    3. Apparier les joueurs restants par backtracking global (voir _find_best_pairing)

    Le résultat minimise les rematches en premier, puis les écarts de score.
    Aucune exception n'est jamais levée.
    """
    rank_map: dict[int, int] = (
        {pid: idx for idx, pid in enumerate(standings_order)}
        if standings_order else {}
    )

    def rank(p: "Player") -> int:
        return rank_map.get(p.id, len(players))

    active = sorted(players, key=rank)

    # --- Bye ---
    bye_player: "Player | None" = None
    if len(active) % 2 == 1:
        bye_player = _select_bye(active, opponents_map, bye_history)
        active = [p for p in active if p.id != bye_player.id]

    # --- Pairing ---
    pairings, had_rematch = _pair_players(active, opponents_map)

    return SwissPairingResult(
        pairings=pairings,
        bye_player=bye_player,
        had_rematch=had_rematch,
    )


def _select_bye(
    players: list["Player"],
    opponents_map: dict[int, set[int]],
    bye_history: set[int],
) -> "Player":
    """
    Sélectionne le joueur qui reçoit le bye.

    Candidats : joueurs sans bye précédent, triés du moins bien classé au mieux.
    Critère : le candidat dont l'absence génère le moins de rematches dans
    les pairings restants. En cas d'égalité, le moins bien classé est préféré.

    Exemple :
        Joueurs [C=3, D=3, A=1, B=1, E=0], A et B ont déjà joué.
        - Essai E : reste [C,D,A,B] → A-B forcé → 1 rematch
        - Essai B : reste [C,D,A,E] → C-D + A-E → 0 rematch ✓
        → B reçoit le bye, C-D et A-E jouent.
    """
    candidates = [p for p in reversed(players) if p.id not in bye_history]
    if not candidates:
        # Tous ont déjà eu un bye → dernier du classement
        candidates = [players[-1]]

    best_bye = candidates[0]
    best_rematches = float('inf')

    for candidate in candidates:
        remaining = [p for p in players if p.id != candidate.id]
        _, rematches, _ = _find_best_pairing(remaining, opponents_map)
        if rematches < best_rematches:
            best_rematches = rematches
            best_bye = candidate
            if rematches == 0:
                break  # Optimal trouvé : aucun rematch possible

    return best_bye


def _pair_players(
    players: list["Player"],
    opponents_map: dict[int, set[int]],
) -> tuple[list[tuple["Player", "Player"]], bool]:
    """
    Appaire une liste paire de joueurs.
    Retourne (pairings, had_rematch).
    """
    pairings_idx, rematches, _ = _find_best_pairing(players, opponents_map)
    result = [(players[i], players[j]) for i, j in pairings_idx]
    return result, rematches > 0


def _find_best_pairing(
    players: list["Player"],
    opponents_map: dict[int, set[int]],
) -> tuple[list[tuple[int, int]], int, int]:
    """
    Trouve le meilleur appariement global par backtracking.

    Critères de priorité :
    1. Minimiser le nombre de rematches (adversaires déjà rencontrés)
    2. Minimiser la somme des écarts de score (paires les plus proches en points)

    Algorithme :
    - Pour chaque joueur (dans l'ordre du classement), essaie tous ses partenaires
      disponibles triés par : (non-rematch d'abord, écart de score croissant)
    - Élagage agressif : abandonne toute branche qui ne peut pas améliorer la solution
    - Sortie précoce dès qu'une solution parfaite (0 rematch, 0 écart) est trouvée
    - Garde-fou : arrêt à 300 000 itérations pour les très grandes listes

    Retourne : (indices_des_paires, nb_rematches, somme_écarts_score)
    """
    n = len(players)
    if n == 0:
        return [], 0, 0

    best = {"rematches": n + 1, "gap": 10 ** 9, "pairings": []}
    iters = [0]

    def is_rematch(i: int, j: int) -> bool:
        return players[j].id in opponents_map.get(players[i].id, set())

    def backtrack(
        available: list[int],
        pairings: list[tuple[int, int]],
        rematches: int,
        gap: int,
    ) -> None:
        iters[0] += 1
        if iters[0] > 300_000:
            return  # Garde-fou : évite les blocages sur de très grandes listes

        # Élagage primaire : trop de rematches accumulés
        if rematches > best["rematches"]:
            return
        # Élagage secondaire : même nombre de rematches mais écart déjà trop grand
        # (gap est monotone croissant, donc il ne peut qu'empirer)
        if rematches == best["rematches"] and gap >= best["gap"]:
            return

        if not available:
            # Solution complète trouvée
            best["rematches"] = rematches
            best["gap"] = gap
            best["pairings"] = pairings[:]
            return

        i = available[0]
        rest = available[1:]

        # Trier les partenaires potentiels :
        # 1. Non-rematch avant rematch (is_rematch : 0 < 1)
        # 2. À type égal : plus proche en score d'abord
        def sort_key(kj: tuple) -> tuple:
            _, j = kj
            return (1 if is_rematch(i, j) else 0, abs(players[i].score - players[j].score))

        for k, j in sorted(enumerate(rest), key=sort_key):
            rem = 1 if is_rematch(i, j) else 0
            new_rem = rematches + rem

            # Dès qu'on dépasse le budget de rematches, tous les suivants aussi
            # (liste triée : rematches viennent après non-rematches)
            if new_rem > best["rematches"]:
                break

            new_gap = gap + abs(players[i].score - players[j].score)
            if new_rem == best["rematches"] and new_gap >= best["gap"]:
                continue  # Ce partenaire ne peut pas améliorer l'écart

            remaining = rest[:k] + rest[k + 1:]
            pairings.append((i, j))
            backtrack(remaining, pairings, new_rem, new_gap)
            pairings.pop()

            # Sortie précoce : solution parfaite (0 rematch, 0 écart de score)
            if best["rematches"] == 0 and best["gap"] == 0:
                return

    backtrack(list(range(n)), [], 0, 0)
    return best["pairings"], best["rematches"], best["gap"]
