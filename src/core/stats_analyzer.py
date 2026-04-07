"""
Analyseur de statistiques pour les tournois et face-à-face.
"""

from dataclasses import dataclass, field
from collections import defaultdict
from core.tournament import Tournament
from core.standings import build_standings
from core.bracket import get_bracket_final_ranking



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

    def __init__(self, tournaments: list[Tournament]):
        self._tournaments = [t for t in tournaments if t.archived]
        self._player_stats: dict[str, PlayerStats] = {}
        self._analyze_all()

    def _normalize_name(self, name: str) -> str:
        """Normalise un nom pour la comparaison."""
        return name.lower().strip()

    def _analyze_all(self):
        """Analyse tous les tournois pour extraire les statistiques."""
        for tournament in self._tournaments:
            self._analyze_tournament(tournament)

    def _analyze_tournament(self, tournament: Tournament):
        """Analyse un tournoi pour extraire les stats des joueurs."""
        players_by_id = {p.id: p for p in tournament.players}

        # Classement Swiss de base
        if tournament.is_1v1_format():
            standings = build_standings(tournament)
            swiss_ordered = [players_by_id[e.player_id] for e in standings if e.player_id in players_by_id]
        else:
            swiss_ordered = sorted(
                tournament.players,
                key=lambda p: (-p.score, -p.robustness, p.name),
            )

        # Si bracket présent, il prime sur le classement Swiss
        if tournament.bracket:
            swiss_ids = [p.id for p in swiss_ordered]
            final_ids = get_bracket_final_ranking(tournament.bracket, swiss_ids)
            ranked = [players_by_id[pid] for pid in final_ids if pid in players_by_id]
        else:
            ranked = swiss_ordered

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

        for rank, player in enumerate(ranked, 1):
            name_key = self._normalize_name(player.name)

            if name_key not in self._player_stats:
                self._player_stats[name_key] = PlayerStats(name=player.name)

            stats = self._player_stats[name_key]
            stats.tournaments_played += 1
            stats.total_points += player.score

            if rank == 1:
                stats.top_1 += 1
            elif rank == 2:
                stats.top_2 += 1
            elif rank == 3:
                stats.top_3 += 1

            p_played, p_won = player_match_stats.get(player.id, (0, 0))
            stats.total_matches += p_played

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
