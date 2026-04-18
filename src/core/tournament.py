from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict
from core.player import Player
from core.round import Round, RoundState
from core.table import Table
from core.swiss_pairing import generate_swiss_pairings, compute_recommended_rounds
from core.standings import build_standings
from core.bracket import Bracket, BracketType, create_bracket_matches
import random

@dataclass
class Tournament:
    id: int
    name: str
    format: str
    date: str

    players: list[Player] = field(default_factory=list)
    rounds: list[Round] = field(default_factory=list)
    max_rounds: int = 3
    archived: bool = False
    podiums_recorded: bool = False

    # Swiss pairing system
    pairing_system: str = "standard"  # "standard" ou "swiss"
    bye_history: set[int] = field(default_factory=set)

    # Phase d'élimination (bracket)
    bracket: Bracket | None = None

    _next_player_id: int = 0

    # =====================
    # Business logic
    # =====================


    ### PLAYER
    @staticmethod
    def create_tournament(*, tournament_id: int, name: str, format: str, date: str, max_rounds: int = 3) -> "Tournament":
        return Tournament(
            id=tournament_id,
            name=name.strip(),
            format=format.strip(),
            date=date,
            players=[],
            max_rounds=max_rounds,
        )

    def add_player(self, name: str, regular_player_id: int | None = None) -> Player | None:
        name = name.strip()
        if not name:
            return None

        # Si le joueur existe déjà mais est dropped → le réinscrire
        existing = next((p for p in self.players if p.name.lower() == name.lower()), None)
        if existing:
            if existing.dropped:
                existing.dropped = False
                if regular_player_id is not None:
                    existing.regular_player_id = regular_player_id
                return existing
            return None  # Déjà inscrit et actif → doublon

        player = Player(
            id=self._next_player_id,
            name=name,
            regular_player_id=regular_player_id,
        )
        self.players.append(player)
        self._next_player_id += 1

        # Invalider les rounds non commencés
        self._invalidate_preparation_rounds()

        return player

    def remove_player(self, player_id: int) -> None:
        self.players = [
            p for p in self.players
            if p.id != player_id
        ]

        # Invalider les rounds non commencés
        self._invalidate_preparation_rounds()

    def _invalidate_preparation_rounds(self) -> None:
        """Supprime les rounds en préparation (tables pas encore jouées)."""
        self.rounds = [
            r for r in self.rounds
            if r.state != RoundState.PREPARATION
        ]

    def rename_player(self, player_id: int, new_name: str) -> bool:
        new_name = new_name.strip()
        if not new_name:
            return False

        if any(p.name.lower() == new_name.lower() for p in self.players):
            return False

        for p in self.players:
            if p.id == player_id:
                p.name = new_name
                return True

        return False

    ### ROUND
    def create_round(self) -> Round | None:
        round_number = len(self.rounds) + 1
        tables = self._generate_tables()

        if tables is None:
            return None

        new_round = Round(
            number=round_number,
            tables=tables
        )

        self.rounds.append(new_round)
        return new_round

    def _generate_tables(self) -> list[Table] | None:
        """
        Génère les tables à partir des scores et de la robustesse,
        en évitant les rematches dès le 2ème round.
        """
        active_players = [p for p in self.players if not p.dropped]
        player_count = len(active_players)
        table_sizes = self.compute_table_sizes(player_count)
        if table_sizes is None:
            return None

        ordered_players = self.sort_players()

        # Premier round (scores tous à 0 → mélange aléatoire) : pas d'anti-rematch
        if not self.rounds:
            tables: list[Table] = []
            idx = 0
            for i, size in enumerate(table_sizes):
                tables.append(Table(number=i + 1, players=ordered_players[idx:idx + size]))
                idx += size
            return tables

        opponents_map = self.get_opponents_map()

        if self.is_1v1_format():
            return self._generate_1v1_tables_anti_rematch(
                ordered_players, opponents_map, table_sizes
            )
        else:
            return self._generate_commander_tables_anti_rematch(
                ordered_players, table_sizes, opponents_map
            )

    def _generate_1v1_tables_anti_rematch(
        self,
        ordered: list["Player"],
        opponents_map: dict[int, set[int]],
        table_sizes: list[int],
    ) -> list[Table]:
        """
        Appariement 1v1 anti-rematch pour le format standard (non-Swiss).

        Si nombre impair de joueurs : choisit le sit-out qui minimise les rematches
        puis les écarts de score, en testant chaque candidat du moins bien classé
        au mieux classé.

        Utilise le même backtracking global que le système Swiss.
        Aucune exception levée : le meilleur pairing possible est toujours retourné.
        """
        from core.swiss_pairing import _find_best_pairing  # noqa: PLC0415

        n_play = sum(table_sizes)

        if len(ordered) > n_play:
            # Nombre impair : sit-out intelligent
            sitout = ordered[-1]  # défaut : dernier du classement
            best_rem, best_gap = float('inf'), float('inf')
            for candidate in reversed(ordered):
                remaining = [p for p in ordered if p.id != candidate.id][:n_play]
                _, rem, gap = _find_best_pairing(remaining, opponents_map)
                if (rem, gap) < (best_rem, best_gap):
                    best_rem, best_gap = rem, gap
                    sitout = candidate
                    if rem == 0:
                        break
            to_pair = [p for p in ordered if p.id != sitout.id][:n_play]
        else:
            to_pair = ordered[:n_play]

        pairings_idx, _, _ = _find_best_pairing(to_pair, opponents_map)
        return [
            Table(number=i + 1, players=[to_pair[a], to_pair[b]])
            for i, (a, b) in enumerate(pairings_idx)
        ]

    def _generate_commander_tables_anti_rematch(
        self,
        ordered: list["Player"],
        table_sizes: list[int],
        opponents_map: dict[int, set[int]],
    ) -> list[Table]:
        """
        Génère les tables Commander (3-4 joueurs) en minimisant les rematches.
        1. Assignation initiale séquentielle par score (tables proches en score).
        2. Optimisation par échanges locaux entre tables adjacentes.
        """
        # Assignation initiale par score
        tables: list[Table] = []
        idx = 0
        for i, size in enumerate(table_sizes):
            tables.append(Table(number=i + 1, players=ordered[idx:idx + size]))
            idx += size

        return _optimize_tables_anti_rematch(tables, opponents_map)

    def compute_table_sizes(self, player_count: int) -> list[int] | None:
        """
        Retourne une liste de tailles de tables (4 ou 3),
        ou None si impossible.
        """
        if self.format == "👑 Commander":
            if player_count < 6:
                return None

            # Cas prioritaire: si divisible par 3, faire des tables de 3
            if player_count % 3 == 0:
                return [3] * (player_count // 3)

            # Sinon chercher la meilleure combinaison 4+3
            max_fours = player_count // 4

            for fours in range(max_fours, -1, -1):
                remaining = player_count - 4 * fours

                if remaining == 0:
                    return [4] * fours

                if remaining % 3 == 0:
                    threes = remaining // 3
                    if threes > 0:
                        return [4] * fours + [3] * threes

            return None

        else:
            if player_count < 4:
                return None

            table_count = player_count // 2
            return [2] * table_count

    def sort_players(self) -> list[Player]:
        """
        Trie les joueurs actifs (non droppés) selon les règles métier.
        """
        active = [p for p in self.players if not p.dropped]
        if all(p.score == 0 for p in active):
            shuffled = active[:]
            random.shuffle(shuffled)
            return shuffled

        return sorted(
            active,
            key=lambda p: (p.score, p.robustness),
            reverse=True
        )

    # =====================
    # Adversaires rencontrés
    # =====================
    def get_opponents_map(self) -> dict[int, set[int]]:
        """Retourne pour chaque joueur l'ensemble des IDs des adversaires déjà rencontrés."""
        opponents: dict[int, set[int]] = {p.id: set() for p in self.players}

        for rnd in self.rounds:
            for table in rnd.tables:
                player_ids = [p.id for p in table.players]
                for pid in player_ids:
                    for other_pid in player_ids:
                        if pid != other_pid:
                            opponents[pid].add(other_pid)

        return opponents

    def recalculate_robustness(self) -> None:
        """
        Recalcule la robustesse de tous les joueurs basée sur le classement actuel.
        Appelée après chaque round terminé.
        """
        # Reset
        for player in self.players:
            player.robustness = 0

        # Classement actuel par score puis nom
        ranked_players = sorted(
            self.players,
            key=lambda p: (-p.score, p.name)
        )
        rank_by_id = {p.id: idx + 1 for idx, p in enumerate(ranked_players)}

        N = len(self.players)

        # Pour chaque round terminé, ajouter la robustesse
        for rnd in self.rounds:
            for table in rnd.tables:
                if not table.finished:
                    continue

                player_ids = [p.id for p in table.players]

                for player in table.players:
                    for opponent_id in player_ids:
                        if opponent_id != player.id:
                            opponent_rank = rank_by_id[opponent_id]
                            player.robustness += (N - opponent_rank)

    def compute_repetition_rate(self, tables: list[Table]) -> float:
        """
        Calcule le taux de répétition pour une liste de tables données.
        Retourne un pourcentage (0-100) des paires de joueurs qui se sont déjà affrontés.
        """
        opponents_map = self.get_opponents_map()

        total_pairs = 0
        repeated_pairs = 0

        for table in tables:
            player_ids = [p.id for p in table.players]
            for i, pid in enumerate(player_ids):
                for other_pid in player_ids[i + 1:]:
                    total_pairs += 1
                    if other_pid in opponents_map.get(pid, set()):
                        repeated_pairs += 1

        if total_pairs == 0:
            return 0.0

        return (repeated_pairs / total_pairs) * 100

    def would_have_repetitions(self) -> tuple[bool, float]:
        """
        Vérifie si la prochaine génération de tables par score aurait des répétitions.
        Retourne (has_repetitions, repetition_rate).
        """
        # Simuler la génération de tables par score (joueurs actifs uniquement)
        active_count = sum(1 for p in self.players if not p.dropped)
        table_sizes = self.compute_table_sizes(active_count)
        if table_sizes is None:
            return False, 0.0

        ordered_players = self.sort_players()

        simulated_tables: list[Table] = []
        index = 0
        table_number = 1

        for size in table_sizes:
            table_players = ordered_players[index:index + size]
            simulated_tables.append(
                Table(number=table_number, players=table_players)
            )
            index += size
            table_number += 1

        rate = self.compute_repetition_rate(simulated_tables)
        # Considérer comme répétitif si plus de 60% de répétitions
        return rate > 50, rate

    def create_round_by_opponents(self) -> Round:
        """
        Crée un round en minimisant les affrontements répétés.
        Utilise un algorithme glouton pour assigner les joueurs aux tables.
        """
        round_number = len(self.rounds) + 1
        tables = self._generate_tables_by_opponents()

        new_round = Round(
            number=round_number,
            tables=tables
        )

        self.rounds.append(new_round)
        return new_round

    def _generate_tables_by_opponents(self) -> list[Table]:
        """
        Génère des tables en minimisant les répétitions et diversifiant la robustesse.
        """
        active_players = [p for p in self.players if not p.dropped]
        table_sizes = self.compute_table_sizes(len(active_players))
        if table_sizes is None:
            return []

        opponents_map = self.get_opponents_map()
        available_players = active_players[:]
        random.shuffle(available_players)  # Mélanger pour ajouter de l'aléatoire

        tables: list[Table] = []
        table_number = 1

        for size in table_sizes:
            table_players: list[Player] = []

            for _ in range(size):
                if not available_players:
                    break

                # Trouver le meilleur joueur (celui qui a le moins de conflits avec la table actuelle)
                best_player = None
                best_score = float('inf')

                for player in available_players:
                    # Compter combien de joueurs de la table actuelle ont déjà été rencontrés
                    conflicts = sum(
                        1 for tp in table_players
                        if tp.id in opponents_map.get(player.id, set())
                    )

                    # Bonus de diversité de robustesse (on veut des robustesses variées)
                    if table_players:
                        avg_rob = sum(tp.robustness for tp in table_players) / len(table_players)
                        # Plus la différence est grande, plus le score diminue (meilleur)
                        diversity_bonus = -abs(player.robustness - avg_rob) * 0.01
                    else:
                        diversity_bonus = 0

                    total_score = conflicts + diversity_bonus

                    if total_score < best_score:
                        best_score = total_score
                        best_player = player

                if best_player:
                    table_players.append(best_player)
                    available_players.remove(best_player)

            if table_players:
                tables.append(
                    Table(number=table_number, players=table_players)
                )
                table_number += 1

        return tables

    # =====================
    # Swiss Pairing System
    # =====================

    def create_round_swiss(self) -> Round:
        """
        Crée un round avec appariement Swiss global anti-rematch.
        Uniquement valide pour les formats 1v1.

        Le pairing minimise les rematches automatiquement — aucune exception levée.
        Le bye est attribué intelligemment pour favoriser les pairings sans rematch.
        """
        round_number = len(self.rounds) + 1
        opponents_map = self.get_opponents_map()

        # Ordre standings complet (match_points → OMW% → GW% → OGW%)
        standings = build_standings(self)
        standings_order = [e.player_id for e in standings]

        active_players = [p for p in self.players if not p.dropped]
        result = generate_swiss_pairings(
            active_players,
            opponents_map,
            self.bye_history,
            standings_order=standings_order,
        )

        tables: list[Table] = []
        for i, (p1, p2) in enumerate(result.pairings, 1):
            tables.append(Table(number=i, players=[p1, p2]))

        # Gérer le bye
        if result.bye_player:
            self.bye_history.add(result.bye_player.id)
            result.bye_player.had_bye = True
            tables.append(Table(
                number=len(tables) + 1,
                players=[result.bye_player],
                finished=True,
                results={result.bye_player.id: 1}
            ))

        new_round = Round(number=round_number, tables=tables)
        self.rounds.append(new_round)
        return new_round

    def calculate_swiss_tiebreakers(self) -> None:
        """
        Calcule les départages Swiss pour tous les joueurs.
        - Buchholz: Somme des scores de tous les adversaires rencontrés
        - SOS: Moyenne des scores des adversaires (Strength of Schedule)

        Doit être appelé après chaque round terminé.
        """
        opponents_map = self.get_opponents_map()

        for player in self.players:
            opponent_ids = opponents_map.get(player.id, set())
            opponent_scores = []

            for opp_id in opponent_ids:
                opp = next((p for p in self.players if p.id == opp_id), None)
                if opp:
                    opponent_scores.append(opp.score)

            player.buchholz = float(sum(opponent_scores))
            player.sos = sum(opponent_scores) / len(opponent_scores) if opponent_scores else 0.0

    def sort_players_swiss(self) -> list[Player]:
        """
        Tri Swiss officiel:
        1. Score (décroissant)
        2. Buchholz (décroissant)
        3. SOS (décroissant)
        4. Nom (alphabétique)
        """
        return sorted(
            self.players,
            key=lambda p: (-p.score, -p.buchholz, -p.sos, p.name)
        )

    def is_swiss_format(self) -> bool:
        """Vérifie si le tournoi utilise l'appariement Swiss."""
        return self.pairing_system == "swiss"

    def is_1v1_format(self) -> bool:
        """True pour tous les formats sauf Commander multiplayer."""
        return self.format != "👑 Commander"

    def get_recommended_rounds(self) -> int:
        """Nombre de rounds recommandé pour Swiss: ceil(log2(n))."""
        return compute_recommended_rounds(len(self.players))

    def update(self, *, name: str, format: str, date: str, max_rounds: int) -> None:
        self.name = name.strip()
        self.format = format.strip()
        self.date = date
        self.max_rounds = max_rounds

    def start_bracket(self, bracket_type: BracketType) -> Bracket:
        """Lance la phase de bracket d'élimination à partir du classement actuel.
        Les joueurs droppés sont exclus du seeding ; on recrute plus loin dans le classement
        pour toujours remplir le bracket.
        """
        standings = build_standings(self)
        dropped_ids = {p.id for p in self.players if p.dropped}

        # Exclure les droppés du seeding, on prend le nombre requis parmi les actifs
        active_seeded_ids = [e.player_id for e in standings if e.player_id not in dropped_ids]

        required = {
            BracketType.FINAL: 4,
            BracketType.DEMI_FINALE: 4,
            BracketType.QUART_DE_FINALE: 8,
        }
        n = min(required[bracket_type], len(active_seeded_ids))
        seeded_ids = active_seeded_ids[:n]

        matches = create_bracket_matches(bracket_type, seeded_ids)
        self.bracket = Bracket(bracket_type=bracket_type, matches=matches)

        # Auto-résoudre les byes (slots vides ou joueurs droppés) dès la création
        self.bracket.auto_resolve_dropped(dropped_ids)

        return self.bracket

    @property
    def is_bracket_phase(self) -> bool:
        """True si le tournoi est en phase de bracket d'élimination."""
        return self.bracket is not None and not self.bracket.finished

    def can_create_round(self) -> bool:
        """Vérifie si on peut créer un nouveau round."""
        if self.bracket is not None:
            return False  # Bracket actif, plus de rounds Swiss
        return len(self.rounds) < self.max_rounds

    def is_finished(self) -> bool:
        """Vérifie si le tournoi est terminé."""
        if not self.rounds:
            return False
        # Vérifier que tous les rounds sont complets
        last_round = self.rounds[-1]
        all_tables_finished = all(t.finished for t in last_round.tables)
        return len(self.rounds) >= self.max_rounds and all_tables_finished

    def restore_from_dict(self, data: dict) -> None:
        """
        Restaure l'état du tournoi depuis un snapshot (undo).
        Modifie l'objet en place pour conserver la même référence mémoire.
        """
        restored = Tournament.from_dict(data)
        self.name = restored.name
        self.format = restored.format
        self.date = restored.date
        self.max_rounds = restored.max_rounds
        self.archived = restored.archived
        self.podiums_recorded = restored.podiums_recorded
        self.pairing_system = restored.pairing_system
        self.players = restored.players
        self.rounds = restored.rounds
        self.bye_history = restored.bye_history
        self.bracket = restored.bracket
        self._next_player_id = restored._next_player_id

    def archive(self) -> None:
        """Archive le tournoi."""
        self.archived = True

    def reset(self) -> None:
        """Réinitialise le tournoi: supprime rounds, tables, résultats et scores."""
        # Réinitialiser les scores des joueurs
        for player in self.players:
            player.score = 0
            player.robustness = 0
            # Reset des champs Swiss
            player.buchholz = 0.0
            player.sos = 0.0
            player.had_bye = False

        # Supprimer tous les rounds (et donc les tables/résultats)
        self.rounds.clear()

        # Réinitialiser l'historique des byes
        self.bye_history.clear()

        # Supprimer le bracket
        self.bracket = None

    @property
    def player_count(self) -> int:
        return len([p for p in self.players if not p.dropped])

    # =====================
    # Tables
    # =====================

    def table_count(self) -> int | None:
        sizes = self.compute_table_sizes(self.player_count)
        return len(sizes) if sizes is not None else None

    # =====================
    # Serialization
    # =====================

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "format": self.format,
            "date": self.date,
            "max_rounds": self.max_rounds,
            "archived": self.archived,
            "podiums_recorded": self.podiums_recorded,
            "pairing_system": self.pairing_system,
            "bye_history": list(self.bye_history),
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "score": p.score,
                    "robustness": p.robustness,
                    "reward_claimed": p.reward_claimed,
                    "commander": p.commander,
                    "buchholz": p.buchholz,
                    "sos": p.sos,
                    "had_bye": p.had_bye,
                    "dropped": p.dropped,
                    "regular_player_id": p.regular_player_id,
                }
                for p in self.players
            ],
            "rounds": [r.to_dict() for r in self.rounds],
            "bracket": self.bracket.to_dict() if self.bracket else None,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Tournament":
        tournament = cls(
            id=data["id"],
            name=data["name"],
            format=data["format"],
            date=data["date"],
            max_rounds=data.get("max_rounds", 3),
            archived=data.get("archived", False),
            podiums_recorded=data.get("podiums_recorded", False),
            pairing_system=data.get("pairing_system", "standard"),
            players=[],
        )

        # Charger l'historique des byes
        tournament.bye_history = set(data.get("bye_history", []))

        # Charger les joueurs
        for p in data.get("players", []):
            player = Player(
                id=p["id"],
                name=p["name"],
                score=p.get("score", 0),
                robustness=p.get("robustness", 0),
                reward_claimed=p.get("reward_claimed", False),
                commander=p.get("commander", ""),
                buchholz=p.get("buchholz", 0.0),
                sos=p.get("sos", 0.0),
                had_bye=p.get("had_bye", False),
                dropped=p.get("dropped", False),
                regular_player_id=p.get("regular_player_id"),
            )
            tournament.players.append(player)
            tournament._next_player_id = max(
                tournament._next_player_id,
                player.id + 1
            )

        # Charger les rounds
        players_by_id = {p.id: p for p in tournament.players}
        for r in data.get("rounds", []):
            round_obj = Round.from_dict(r, players_by_id)
            tournament.rounds.append(round_obj)

        # Charger le bracket
        bracket_data = data.get("bracket")
        if bracket_data:
            tournament.bracket = Bracket.from_dict(bracket_data)

        return tournament


# =====================
# Optimisation anti-rematch (Commander)
# =====================

def _optimize_tables_anti_rematch(
    tables: list[Table],
    opponents_map: dict[int, set[int]],
) -> list[Table]:
    """
    Réduit les rematches par échanges locaux entre tables adjacentes (score-proches).

    Algorithme : hill-climbing — à chaque passe, on cherche l'échange entre deux
    joueurs de tables voisines (±2 positions) qui réduit le plus le nombre total
    de rematches. On itère jusqu'à convergence ou 30 passes max.

    Un « rematch » = deux joueurs dans la même table qui se sont déjà affrontés.
    """

    def table_conflicts(players: list) -> int:
        total = 0
        for i, p1 in enumerate(players):
            for p2 in players[i + 1:]:
                if p2.id in opponents_map.get(p1.id, set()):
                    total += 1
        return total

    # Travailler sur des listes mutables
    groups: list[list] = [list(t.players) for t in tables]
    n = len(groups)

    for _ in range(30):
        improved = False

        for ti in range(n):
            c_ti = table_conflicts(groups[ti])
            if c_ti == 0:
                continue  # Table sans conflit, on passe

            # Chercher le meilleur échange avec une table voisine (±2)
            best_delta = 0
            best_swap: tuple | None = None

            for tj in range(max(0, ti - 2), min(n, ti + 3)):
                if ti == tj:
                    continue
                c_tj = table_conflicts(groups[tj])
                current = c_ti + c_tj

                for pi, p1 in enumerate(groups[ti]):
                    for pj, p2 in enumerate(groups[tj]):
                        new_ti = groups[ti][:pi] + [p2] + groups[ti][pi + 1:]
                        new_tj = groups[tj][:pj] + [p1] + groups[tj][pj + 1:]
                        delta = table_conflicts(new_ti) + table_conflicts(new_tj) - current
                        if delta < best_delta:
                            best_delta = delta
                            best_swap = (ti, tj, new_ti, new_tj)

            if best_swap:
                ti_s, tj_s, new_ti, new_tj = best_swap
                groups[ti_s] = new_ti
                groups[tj_s] = new_tj
                improved = True
                break  # Recommencer depuis le début

        if not improved:
            break  # Plus aucun échange bénéfique → convergence

    return [Table(number=t.number, players=g) for t, g in zip(tables, groups)]


# =====================
# Utils
# =====================

def next_free_tournament_id(tournaments: list[Tournament]) -> int:
    if not tournaments:
        return 0
    return max(t.id for t in tournaments) + 1


def parse_tournament_date(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, "%d/%m/%Y")
    except ValueError:
        return datetime.max


def sort_tournaments_by_date(tournaments: list[Tournament]) -> list[Tournament]:
    return sorted(
        tournaments,
        key=lambda t: parse_tournament_date(t.date)
    )
