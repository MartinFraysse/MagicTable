"""
Analyseur de statistiques pour les tournois et face-à-face.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from collections import defaultdict
from typing import TYPE_CHECKING

from core.tournament import Tournament
from core.ranking import final_ranking

if TYPE_CHECKING:
    from core.player import Player
    from core.regular_player import RegularPlayer



@dataclass
class HeadToHeadResult:
    """Résultat d'une confrontation entre deux joueurs."""
    tournament_name: str
    tournament_date: str
    round_number: int
    table_number: int
    player_position: int
    opponent_position: int
    is_bracket: bool = False
    bracket_round_name: str = ""

    @property
    def is_win(self) -> bool:
        return self.player_position < self.opponent_position

    @property
    def is_loss(self) -> bool:
        return self.player_position > self.opponent_position


@dataclass
class MatchupStats:
    """Statistiques de confrontation avec un adversaire."""
    opponent_name: str
    total_matches: int = 0
    wins: int = 0
    losses: int = 0
    history: list[HeadToHeadResult] = field(default_factory=list)

    @property
    def winrate(self) -> float:
        if self.total_matches == 0:
            return 0.0
        return (self.wins / self.total_matches) * 100


@dataclass
class PlayerStats:
    """Statistiques globales d'un joueur."""
    name: str
    tournaments_played: int = 0
    total_matches: int = 0
    top_1: int = 0
    top_2: int = 0
    top_3: int = 0
    total_points: int = 0
    @property
    def total_podiums(self) -> int:
        return self.top_1 + self.top_2 + self.top_3


class StatsAnalyzer:
    """Analyseur de statistiques pour les tournois."""

    def __init__(
        self,
        tournaments: list[Tournament],
        regular_players: list[RegularPlayer] | None = None,
    ):
        self._tournaments = [t for t in tournaments if t.archived]
        self._player_stats: dict[str, PlayerStats] = {}

        # Stats par joueur régulier (source unique pour les vues Joueurs / Stats)
        self._regular_players = list(regular_players or [])
        self._regular_ids = {rp.id for rp in self._regular_players}
        self._regular_by_pseudo = {
            self._normalize_name(rp.pseudo): rp.id for rp in self._regular_players
        }
        self._regular_stats: dict[int, PlayerStats] = {
            rp.id: PlayerStats(name=rp.pseudo) for rp in self._regular_players
        }

        self._analyze_all()

    def _normalize_name(self, name: str) -> str:
        """Normalise un nom pour la comparaison."""
        return name.lower().strip()

    def _resolve_regular_id(self, player: Player) -> int | None:
        """
        Joueur régulier correspondant à un joueur de tournoi :
        lien explicite (regular_player_id) en priorité, sinon pseudo identique
        (tournois archivés avant l'introduction du lien).
        """
        if player.regular_player_id in self._regular_ids:
            return player.regular_player_id
        if player.regular_player_id is not None:
            return None  # lien vers un joueur régulier supprimé
        return self._regular_by_pseudo.get(self._normalize_name(player.name))

    def _analyze_all(self):
        """Analyse tous les tournois pour extraire les statistiques."""
        for tournament in self._tournaments:
            self._analyze_tournament(tournament)

    def _analyze_tournament(self, tournament: Tournament):
        """Analyse un tournoi pour extraire les stats des joueurs."""
        # Classement final (bracket prioritaire sur les rondes)
        ranked = final_ranking(tournament)

        # Pré-calculer les matchs individuels (victoires/défaites) par joueur
        player_match_stats: dict[int, tuple[int, int]] = {}  # id -> (played, won)
        for player in tournament.players:
            played = 0
            won = 0
            # Rounds Swiss / standard
            for rnd in tournament.rounds:
                for table in rnd.tables:
                    p_ids = [p.id for p in table.players]
                    if player.id not in p_ids:
                        continue
                    if len(p_ids) == 1:
                        continue  # BYE, ne compte pas
                    played += 1
                    if table.results.get(player.id, 99) == 1:
                        won += 1
            # Bracket
            if tournament.bracket:
                for match in tournament.bracket.matches:
                    if player.id not in (match.player1_id, match.player2_id):
                        continue
                    if not match.finished:
                        continue
                    played += 1
                    if match.winner_id == player.id:
                        won += 1
            player_match_stats[player.id] = (played, won)

        counted_regulars: set[int] = set()
        for rank, player in enumerate(ranked, 1):
            name_key = self._normalize_name(player.name)

            if name_key not in self._player_stats:
                self._player_stats[name_key] = PlayerStats(name=player.name)

            p_played, _ = player_match_stats.get(player.id, (0, 0))
            targets = [self._player_stats[name_key]]

            rp_id = self._resolve_regular_id(player)
            if rp_id is not None and rp_id not in counted_regulars:
                counted_regulars.add(rp_id)
                targets.append(self._regular_stats[rp_id])

            for stats in targets:
                stats.tournaments_played += 1
                stats.total_points += player.score
                stats.total_matches += p_played
                if rank == 1:
                    stats.top_1 += 1
                elif rank == 2:
                    stats.top_2 += 1
                elif rank == 3:
                    stats.top_3 += 1

    def get_global_stats(self) -> dict:
        """Retourne les statistiques globales."""
        total_matches = 0
        for tournament in self._tournaments:
            for rnd in tournament.rounds:
                total_matches += len(rnd.tables)

        unique_players = set()
        for tournament in self._tournaments:
            for player in tournament.players:
                unique_players.add(self._normalize_name(player.name))

        return {
            "total_tournaments": len(self._tournaments),
            "total_unique_players": len(unique_players),
            "total_tables": total_matches,
        }

    def get_format_distribution(self) -> dict[str, int]:
        """Retourne la distribution des formats de tournoi."""
        formats: dict[str, int] = defaultdict(int)
        for tournament in self._tournaments:
            # Nettoyer le format (enlever les emojis pour l'agrégation)
            fmt = tournament.format
            formats[fmt] += 1
        return dict(formats)

    def get_top_players(self, limit: int = 10) -> list[PlayerStats]:
        """Retourne les meilleurs joueurs triés par victoires."""
        players = list(self._player_stats.values())
        # Trier par top_1, puis top_2, puis top_3, puis points
        players.sort(key=lambda p: (-p.top_1, -p.top_2, -p.top_3, -p.total_points))
        return players[:limit]

    def get_regular_player_stats(self, regular_player_id: int) -> PlayerStats:
        """Stats cumulées d'un joueur régulier (zéros s'il n'a joué aucun tournoi archivé)."""
        return self._regular_stats.get(regular_player_id) or PlayerStats(name="")

    def get_regular_players_ranking(self) -> list[PlayerStats]:
        """Joueurs réguliers ayant joué au moins un tournoi archivé, triés comme get_top_players."""
        players = [s for s in self._regular_stats.values() if s.tournaments_played > 0]
        players.sort(key=lambda p: (-p.top_1, -p.top_2, -p.top_3, -p.total_points))
        return players

    def get_all_players(self) -> list[str]:
        """Retourne la liste de tous les joueurs uniques."""
        players = set()
        for tournament in self._tournaments:
            for player in tournament.players:
                players.add(player.name)
        return sorted(players, key=str.lower)

    def get_player_matchups(self, player_name: str) -> list[MatchupStats]:
        """Retourne les statistiques de confrontation pour un joueur."""
        player_key = self._normalize_name(player_name)
        matchups: dict[str, MatchupStats] = {}

        for tournament in self._tournaments:
            # Trouver le joueur dans ce tournoi
            player_in_tournament = None
            for p in tournament.players:
                if self._normalize_name(p.name) == player_key:
                    player_in_tournament = p
                    break

            if not player_in_tournament:
                continue

            # Parcourir toutes les tables
            for rnd in tournament.rounds:
                for table in rnd.tables:
                    # Vérifier si le joueur est dans cette table
                    player_at_table = None
                    for p in table.players:
                        if self._normalize_name(p.name) == player_key:
                            player_at_table = p
                            break

                    if not player_at_table:
                        continue

                    # Obtenir la position du joueur
                    player_position = table.results.get(player_at_table.id, 99)

                    # Parcourir les adversaires
                    for opponent in table.players:
                        if opponent.id == player_at_table.id:
                            continue

                        opponent_key = self._normalize_name(opponent.name)
                        opponent_position = table.results.get(opponent.id, 99)

                        # Créer ou mettre à jour les stats
                        if opponent_key not in matchups:
                            matchups[opponent_key] = MatchupStats(opponent_name=opponent.name)

                        stats = matchups[opponent_key]
                        stats.total_matches += 1

                        result = HeadToHeadResult(
                            tournament_name=tournament.name,
                            tournament_date=tournament.date,
                            round_number=rnd.number,
                            table_number=table.number,
                            player_position=player_position,
                            opponent_position=opponent_position
                        )

                        if result.is_win:
                            stats.wins += 1
                        elif result.is_loss:
                            stats.losses += 1

                        stats.history.append(result)

            # Parcourir les matches de bracket
            if tournament.bracket:
                _BRACKET_ROUND_LABELS = {
                    "quart": "Quart de finale",
                    "demi":  "Demi-finale",
                    "final": "Finale",
                }
                players_by_id = {p.id: p for p in tournament.players}
                for match in tournament.bracket.matches:
                    if not match.finished or match.winner_id is None:
                        continue
                    p1 = players_by_id.get(match.player1_id)
                    p2 = players_by_id.get(match.player2_id)
                    if p1 is None or p2 is None:
                        continue

                    p1_key = self._normalize_name(p1.name)
                    p2_key = self._normalize_name(p2.name)

                    if p1_key == player_key:
                        our_id, opponent, opponent_key = p1.id, p2, p2_key
                    elif p2_key == player_key:
                        our_id, opponent, opponent_key = p2.id, p1, p1_key
                    else:
                        continue

                    if opponent_key not in matchups:
                        matchups[opponent_key] = MatchupStats(opponent_name=opponent.name)

                    m_stats = matchups[opponent_key]
                    m_stats.total_matches += 1

                    is_winner = match.winner_id == our_id
                    round_label = _BRACKET_ROUND_LABELS.get(match.round_name.value, "Bracket")

                    h2h = HeadToHeadResult(
                        tournament_name=tournament.name,
                        tournament_date=tournament.date,
                        round_number=0,
                        table_number=0,
                        player_position=1 if is_winner else 2,
                        opponent_position=2 if is_winner else 1,
                        is_bracket=True,
                        bracket_round_name=round_label,
                    )
                    if is_winner:
                        m_stats.wins += 1
                    else:
                        m_stats.losses += 1
                    m_stats.history.append(h2h)

        # Trier par nombre de matchs décroissant
        result = list(matchups.values())
        result.sort(key=lambda m: (-m.total_matches, -m.wins, m.opponent_name.lower()))
        return result

    def get_head_to_head(self, player_name: str, opponent_name: str) -> MatchupStats | None:
        """Retourne les stats détaillées entre deux joueurs."""
        matchups = self.get_player_matchups(player_name)
        opponent_key = self._normalize_name(opponent_name)

        for matchup in matchups:
            if self._normalize_name(matchup.opponent_name) == opponent_key:
                return matchup

        return None
