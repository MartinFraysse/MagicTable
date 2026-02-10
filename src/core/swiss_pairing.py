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
    bye_history: set[int]
) -> SwissPairingResult:
    """
    Génère les appariements Swiss pour un round.

    Algorithme:
    1. Si nombre impair: assigner bye au joueur avec le plus bas score
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

    Returns:
        SwissPairingResult avec les pairings et le joueur bye (si applicable)
    """
    bye_player = None
    active_players = players[:]

    # Gérer nombre impair - assigner bye
    if len(active_players) % 2 == 1:
        # Trier par score croissant (plus bas score = priorité pour bye)
        sorted_by_score = sorted(
            active_players,
            key=lambda p: (p.score, random.random())
        )

        # Trouver le premier joueur sans bye précédent
        for player in sorted_by_score:
            if player.id not in bye_history:
                bye_player = player
                active_players.remove(player)
                break

        # Si tous ont eu un bye, donner au plus bas score
        if bye_player is None and sorted_by_score:
            bye_player = sorted_by_score[0]
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

    # Forcer l'appariement des floaters restants (rematches autorisés)
    if len(floaters) >= 2:
        for i in range(0, len(floaters) - 1, 2):
            pairings.append((floaters[i], floaters[i + 1]))

    return SwissPairingResult(pairings=pairings, bye_player=bye_player)


def _pair_bracket(
    players: list["Player"],
    opponents_map: dict[int, set[int]]
) -> tuple[list[tuple["Player", "Player"]], list["Player"]]:
    """
    Apparie les joueurs d'un bracket en évitant les rematches.

    Utilise un algorithme glouton:
    - Pour chaque joueur non apparié, chercher un adversaire valide
    - Un adversaire est valide s'il n'a pas déjà été rencontré
    - Les joueurs sans adversaire valide sont retournés comme floaters

    Args:
        players: Joueurs du bracket à apparier
        opponents_map: Historique des adversaires

    Returns:
        (pairings, unpaired) - Les appariements réussis et les joueurs non appariés
    """
    if len(players) < 2:
        return [], players

    pairings: list[tuple["Player", "Player"]] = []
    available = list(range(len(players)))

    while len(available) >= 2:
        found_pair = False
        i = available[0]

        # Chercher un adversaire valide pour le joueur i
        for j in available[1:]:
            p1, p2 = players[i], players[j]

            # Vérifier si c'est un rematch
            if p2.id in opponents_map.get(p1.id, set()):
                continue

            # Appariement valide trouvé
            pairings.append((p1, p2))
            available.remove(i)
            available.remove(j)
            found_pair = True
            break

        if not found_pair:
            # Aucun adversaire valide, ces joueurs vont flotter
            break

    unpaired = [players[i] for i in available]
    return pairings, unpaired
