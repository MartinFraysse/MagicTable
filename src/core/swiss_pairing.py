"""
Système d'appariement Swiss officiel.

Règles implémentées :
- Tri par standings complets : match_points → OMW% → GW% → OGW%
- Appariement par bracket de score (joueurs de même score s'affrontent)
- Dans chaque bracket : rang le plus proche d'abord (1vs2, 3vs4, ...)
- Anti-rematch : backtracking pour trouver le swap le plus proche
- Floaters : joueurs non appariés descendent au bracket inférieur (comportement normal)
- Bye : joueur le moins bien classé sans bye précédent
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
    rematch_forced: bool = False


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

    Algorithme :
    1. Trier les joueurs par standings_order (match_points + OMW% + GW% + OGW%)
    2. Si nombre impair : bye au joueur le moins bien classé sans bye précédent
    3. Grouper par bracket de score (match_points identiques)
    4. Dans chaque bracket (du plus haut au plus bas) :
       - Combiner les floaters du bracket précédent + joueurs du bracket actuel
       - Trier le groupe combiné par rang
       - Apparier rang 1 vs rang 2, rang 3 vs rang 4, etc. (anti-rematch via backtracking)
       - Les joueurs non appariés « flottent » vers le bracket inférieur
    5. Forcer l'appariement des floaters restants (rematches inévitables)

    Args :
        players        : Liste des joueurs à apparier.
        opponents_map  : {player_id → set(opponent_ids déjà rencontrés)}.
        bye_history    : Set des player_ids ayant déjà reçu un bye.
        standings_order: Liste d'IDs du meilleur (index 0) au moins bon — produite
                         par build_standings() : match_points → OMW% → GW% → OGW%.

    Returns :
        SwissPairingResult avec pairings et bye_player éventuel.
    """
    # Construire la table rang → index (plus petit = meilleur)
    rank_map: dict[int, int] = (
        {pid: idx for idx, pid in enumerate(standings_order)}
        if standings_order
        else {}
    )

    def rank(p: "Player") -> int:
        return rank_map.get(p.id, len(players))

    # --- Étape 1 : trier par standings ---
    active_players = sorted(players, key=rank)

    # --- Étape 2 : bye (nombre impair) ---
    bye_player: "Player | None" = None

    if len(active_players) % 2 == 1:
        # Chercher depuis le bas du classement le premier sans bye
        for p in reversed(active_players):
            if p.id not in bye_history:
                bye_player = p
                active_players.remove(p)
                break

        # Si tous ont déjà eu un bye → dernier du classement
        if bye_player is None:
            bye_player = active_players.pop()

    # --- Étape 3 : grouper par bracket de score ---
    # active_players est déjà trié → chaque bracket conserve l'ordre standings
    score_brackets: dict[int, list["Player"]] = {}
    for p in active_players:
        score_brackets.setdefault(p.score, []).append(p)

    # --- Étape 4 : apparier bracket par bracket ---
    pairings: list[tuple["Player", "Player"]] = []
    floaters: list["Player"] = []
    rematch_forced = False

    for score in sorted(score_brackets.keys(), reverse=True):
        # Floaters du bracket précédent + joueurs du bracket actuel, re-triés par rang
        group = sorted(floaters + score_brackets[score], key=rank)
        floaters = []

        paired, unpaired = _pair_group(group, opponents_map)
        pairings.extend(paired)
        floaters = unpaired

    # --- Étape 5 : floaters restants (rematches inévitables) ---
    if len(floaters) >= 2:
        for i in range(0, len(floaters) - 1, 2):
            pairings.append((floaters[i], floaters[i + 1]))
        rematch_forced = True

    return SwissPairingResult(
        pairings=pairings,
        bye_player=bye_player,
        rematch_forced=rematch_forced,
    )


def _pair_group(
    players: list["Player"],
    opponents_map: dict[int, set[int]],
) -> tuple[list[tuple["Player", "Player"]], list["Player"]]:
    """
    Apparie les joueurs d'un groupe (déjà triés par rang standings).

    Utilise un backtracking pour minimiser le nombre de floaters tout en
    préférant les pairings les plus proches en rang (l'ordre d'exploration
    est naturellement rang 1 vs rang 2, puis 3 vs 4, etc.).

    Returns :
        (pairings, floaters) — appariements réussis et joueurs non appariés.
    """
    if len(players) < 2:
        return [], list(players)

    n = len(players)
    best_floater_count = [n + 1]
    best_result: list[tuple[list, list] | None] = [None]

    def backtrack(
        available: list[int],
        pairings: list[tuple[int, int]],
        floaters: list[int],
    ) -> None:
        # Élagage : impossible de faire mieux que le meilleur connu
        if len(floaters) >= best_floater_count[0]:
            return

        if len(available) < 2:
            all_floaters = floaters + available
            if len(all_floaters) < best_floater_count[0]:
                best_floater_count[0] = len(all_floaters)
                best_result[0] = (pairings[:], all_floaters[:])
            return

        # Court-circuit : solution optimale déjà trouvée
        if best_floater_count[0] == 0:
            return

        i = available[0]
        rest = available[1:]
        has_valid_partner = False

        # Essayer les partenaires dans l'ordre du rang (le plus proche d'abord)
        for k, j in enumerate(rest):
            if players[j].id not in opponents_map.get(players[i].id, set()):
                has_valid_partner = True
                remaining = rest[:k] + rest[k + 1:]
                pairings.append((i, j))
                backtrack(remaining, pairings, floaters)
                pairings.pop()
                if best_floater_count[0] == 0:
                    return

        # Aucun partenaire valide dans ce groupe → i devient floater
        if not has_valid_partner:
            backtrack(rest, pairings, floaters + [i])

    backtrack(list(range(n)), [], [])

    if best_result[0] is None:
        return [], list(players)

    pairings_idx, floaters_idx = best_result[0]
    result_pairings = [(players[i], players[j]) for i, j in pairings_idx]
    result_floaters = [players[i] for i in floaters_idx]
    return result_pairings, result_floaters
