"""
Système d'appariement Swiss officiel.

Règles implémentées:
- Appariement par bracket de score (joueurs de même score s'affrontent)
- Pas de rematches (deux joueurs ne se rencontrent qu'une fois)
- Bye automatique pour nombre impair (joueur avec plus bas score sans bye précédent)
- Floaters: joueurs non appariés descendent au bracket inférieur
"""
import math
import random
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
    large_gap: bool = False  # True si au moins un pairing a un écart de rang trop important


def compute_recommended_rounds(player_count: int) -> int:
    """
    Calcule le nombre de rounds recommandé pour un tournoi Swiss.
    Formule: ceil(log2(n))

    Exemples:
    - 4-8 joueurs: 3 rounds
    - 9-16 joueurs: 4 rounds
    - 17-32 joueurs: 5 rounds
    - 33-64 joueurs: 6 rounds
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

    Algorithme:
    1. Si nombre impair: assigner bye au dernier joueur du classement
       qui n'a pas encore reçu de bye
    2. Grouper les joueurs restants par bracket de score
    3. Dans chaque bracket (du plus haut au plus bas):
       - Apparier les joueurs en évitant les rematches
       - Les joueurs non appariés "flottent" vers le bracket inférieur
    4. Forcer l'appariement des floaters restants (rematches si nécessaire)

    Args:
        players: Liste des joueurs à apparier
        opponents_map: Dict {player_id: set(opponent_ids déjà rencontrés)}
        bye_history: Set des player_ids ayant déjà reçu un bye
        standings_order: Liste d'IDs joueurs du meilleur au moins bon (pour le bye)

    Returns:
        SwissPairingResult avec les pairings et le joueur bye (si applicable)
    """
    bye_player = None
    active_players = players[:]

    # Gérer nombre impair - assigner bye
    if len(active_players) % 2 == 1:
        player_map = {p.id: p for p in active_players}

        if standings_order:
            # Itérer du dernier au premier dans le classement
            candidates = [
                player_map[pid]
                for pid in reversed(standings_order)
                if pid in player_map
            ]
        else:
            # Fallback : trier par score croissant
            candidates = sorted(active_players, key=lambda p: (p.score, random.random()))

        # Trouver le premier candidat sans bye précédent
        for player in candidates:
            if player.id not in bye_history:
                bye_player = player
                active_players.remove(player)
                break

        # Si tous ont eu un bye, donner au dernier du classement
        if bye_player is None and candidates:
            bye_player = candidates[0]
            active_players.remove(bye_player)

    # Grouper par score brackets
    score_brackets: dict[int, list["Player"]] = {}
    for player in active_players:
        if player.score not in score_brackets:
            score_brackets[player.score] = []
        score_brackets[player.score].append(player)

    # Apparier par bracket (du plus haut score au plus bas)
    pairings: list[tuple["Player", "Player"]] = []
    floaters: list["Player"] = []

    for score in sorted(score_brackets.keys(), reverse=True):
        # Combiner floaters du bracket précédent avec le bracket actuel
        bracket_players = floaters + score_brackets[score]
        random.shuffle(bracket_players)  # Randomiser l'ordre dans le bracket
        floaters = []

        # Apparier dans ce bracket
        paired, unpaired = _pair_bracket(bracket_players, opponents_map)
        pairings.extend(paired)
        floaters = unpaired

    # Si des floaters restent, les rematches sont inévitables — on les force et on signale
    if len(floaters) >= 2:
        for i in range(0, len(floaters) - 1, 2):
            pairings.append((floaters[i], floaters[i + 1]))
        return SwissPairingResult(pairings=pairings, bye_player=bye_player, rematch_forced=True)

    large_gap = _has_large_gap(pairings, standings_order)
    return SwissPairingResult(pairings=pairings, bye_player=bye_player, large_gap=large_gap)


def _has_large_gap(
    pairings: list[tuple["Player", "Player"]],
    standings_order: list[int] | None,
) -> bool:
    """
    Retourne True si au moins un pairing présente un écart de rang trop important.
    Seuil : gap > max(2, nb_joueurs // 2).
    """
    if not standings_order or not pairings:
        return False

    rank_map = {pid: idx for idx, pid in enumerate(standings_order)}
    threshold = max(2, len(standings_order) // 2)

    for p1, p2 in pairings:
        r1 = rank_map.get(p1.id)
        r2 = rank_map.get(p2.id)
        if r1 is not None and r2 is not None and abs(r1 - r2) > threshold:
            return True
    return False


def _pair_bracket(
    players: list["Player"],
    opponents_map: dict[int, set[int]]
) -> tuple[list[tuple["Player", "Player"]], list["Player"]]:
    """
    Apparie les joueurs d'un bracket en évitant les rematches.

    Utilise un backtracking pour maximiser les appariements sans rematch :
    - Pour chaque joueur, on essaie tous ses partenaires valides (sans rematch)
    - Si aucun partenaire valide n'existe, le joueur devient floater
    - On garde la solution avec le moins de floaters possible

    Args:
        players: Joueurs du bracket à apparier
        opponents_map: Historique des adversaires

    Returns:
        (pairings, unpaired) - Les appariements réussis et les joueurs non appariés
    """
    if len(players) < 2:
        return [], players

    n = len(players)
    best_floater_count = [n + 1]
    best_result: list[tuple[list, list] | None] = [None]

    def backtrack(available: list[int], pairings: list[tuple[int, int]], floaters: list[int]) -> None:
        # Élagage: impossible de faire mieux que le meilleur connu
        if len(floaters) >= best_floater_count[0]:
            return

        if len(available) < 2:
            all_floaters = floaters + available
            if len(all_floaters) < best_floater_count[0]:
                best_floater_count[0] = len(all_floaters)
                best_result[0] = (pairings[:], all_floaters[:])
            return

        # Solution optimale déjà trouvée
        if best_floater_count[0] == 0:
            return

        i = available[0]
        rest = available[1:]
        has_valid_partner = False

        for k, j in enumerate(rest):
            if players[j].id not in opponents_map.get(players[i].id, set()):
                has_valid_partner = True
                remaining = rest[:k] + rest[k + 1:]
                pairings.append((i, j))
                backtrack(remaining, pairings, floaters)
                pairings.pop()
                if best_floater_count[0] == 0:
                    return

        # Si aucun partenaire valide, i doit forcément flotter
        if not has_valid_partner:
            backtrack(rest, pairings, floaters + [i])

    backtrack(list(range(n)), [], [])

    if best_result[0] is None:
        return [], players

    pairings_idx, floaters_idx = best_result[0]
    result_pairings = [(players[i], players[j]) for i, j in pairings_idx]
    result_floaters = [players[i] for i in floaters_idx]
    return result_pairings, result_floaters
