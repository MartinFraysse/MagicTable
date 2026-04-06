"""
Analyseur de statistiques pour les tournois et face-à-face.
"""

from dataclasses import dataclass, field
from collections import defaultdict
from core.tournament import Tournament
from core.standings import build_standings
from core.bracket import get_bracket_final_ranking


@dataclass
class CommanderEntry:
    """Commandant joue par un joueur dans un tournoi."""
    commander_name: str
    format: str
    tournament_name: str
    tournament_date: str
    rank: int = 0
    matches_played: int = 0   # matchs individuels joués dans ce tournoi
    matches_won: int = 0      # matchs individuels gagnés dans ce tournoi


@dataclass
class CommanderStats:
    """Statistiques agrégées d'un commandant pour un joueur."""
    commander_name: str
    played: int = 0           # tournois joués
    top1: int = 0
    top2: int = 0
    top3: int = 0
    matches_played: int = 0   # total matchs individuels
    matches_won: int = 0      # total matchs individuels gagnés

    @property
    def winrate(self) -> float:
        if self.matches_played == 0:
            return 0.0
        return (self.matches_won / self.matches_played) * 100


@dataclass
class CommanderMatchup:
    """Confrontation d'un commandant contre un commandant adverse."""
    opponent_commander: str
    matches_played: int = 0
    matches_won: int = 0

    @property
    def winrate(self) -> float:
        if self.matches_played == 0:
            return 0.0
        return (self.matches_won / self.matches_played) * 100


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
    commanders: list[CommanderEntry] = field(default_factory=list)

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

            # Collecter le commandant joue
            if player.commander:
                stats.commanders.append(CommanderEntry(
                    commander_name=player.commander,
                    format=tournament.format,
                    tournament_name=tournament.name,
                    tournament_date=tournament.date,
                    rank=rank,
                    matches_played=p_played,
                    matches_won=p_won,
                ))

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

    def get_player_commander_stats(self, player_name: str, fmt: str) -> list[CommanderStats]:
        """
        Retourne les stats agrégées par commandant pour un joueur dans un format donné.
        Triées par nombre de parties jouées décroissant, puis win rate décroissant.
        """
        player_key = self._normalize_name(player_name)
        player_stats = self._player_stats.get(player_key)
        if not player_stats:
            return []

        agg: dict[str, CommanderStats] = {}
        for entry in player_stats.commanders:
            if entry.format != fmt:
                continue
            cmd = entry.commander_name
            if cmd not in agg:
                agg[cmd] = CommanderStats(commander_name=cmd)
            s = agg[cmd]
            s.played += 1
            s.matches_played += entry.matches_played
            s.matches_won += entry.matches_won
            if entry.rank == 1:
                s.top1 += 1
            elif entry.rank == 2:
                s.top2 += 1
            elif entry.rank == 3:
                s.top3 += 1

        result = list(agg.values())
        result.sort(key=lambda x: (-x.winrate, -x.played, x.commander_name.lower()))
        return result

    def get_global_commander_stats(self, fmt: str) -> list[CommanderStats]:
        """
        Retourne les stats agrégées de TOUS les commandants pour un format donné,
        tous joueurs confondus.
        Win rate basé sur les matchs individuels (pas le classement final).
        Triées par win rate décroissant, puis matchs joués décroissant.
        """
        agg: dict[str, CommanderStats] = {}
        for player_stats in self._player_stats.values():
            for entry in player_stats.commanders:
                if entry.format != fmt:
                    continue
                cmd = entry.commander_name
                if cmd not in agg:
                    agg[cmd] = CommanderStats(commander_name=cmd)
                s = agg[cmd]
                s.played += 1
                s.matches_played += entry.matches_played
                s.matches_won += entry.matches_won
                if entry.rank == 1:
                    s.top1 += 1
                elif entry.rank == 2:
                    s.top2 += 1
                elif entry.rank == 3:
                    s.top3 += 1

        result = list(agg.values())
        result.sort(key=lambda x: (-x.winrate, -x.matches_played, x.commander_name.lower()))
        return result

    def get_commander_matchups(self, commander_name: str, fmt: str) -> list[CommanderMatchup]:
        """
        Retourne les confrontations d'un commandant contre tous les commandants adverses,
        dans un format donné. Win rate basé sur les matchs individuels.
        """
        cmd_key = self._normalize_name(commander_name)
        agg: dict[str, CommanderMatchup] = {}

        for tournament in self._tournaments:
            if tournament.format != fmt:
                continue

            players_by_id = {p.id: p for p in tournament.players}

            # Rounds Swiss / standard
            for rnd in tournament.rounds:
                for table in rnd.tables:
                    if len(table.players) < 2:
                        continue  # BYE

                    # Trouver si notre commandant est à cette table
                    our_player = next(
                        (p for p in table.players
                         if p.commander and self._normalize_name(p.commander) == cmd_key),
                        None,
                    )
                    if our_player is None:
                        continue

                    our_win = table.results.get(our_player.id, 99) == 1

                    for opp in table.players:
                        if opp.id == our_player.id or not opp.commander:
                            continue
                        opp_cmd = opp.commander
                        if opp_cmd not in agg:
                            agg[opp_cmd] = CommanderMatchup(opponent_commander=opp_cmd)
                        m = agg[opp_cmd]
                        m.matches_played += 1
                        if our_win:
                            m.matches_won += 1

            # Bracket
            if tournament.bracket:
                for match in tournament.bracket.matches:
                    if not match.finished:
                        continue
                    p1 = players_by_id.get(match.player1_id)
                    p2 = players_by_id.get(match.player2_id)
                    if not p1 or not p2:
                        continue

                    if p1.commander and self._normalize_name(p1.commander) == cmd_key:
                        our_player, opp = p1, p2
                    elif p2.commander and self._normalize_name(p2.commander) == cmd_key:
                        our_player, opp = p2, p1
                    else:
                        continue

                    if not opp.commander:
                        continue
                    opp_cmd = opp.commander
                    if opp_cmd not in agg:
                        agg[opp_cmd] = CommanderMatchup(opponent_commander=opp_cmd)
                    m = agg[opp_cmd]
                    m.matches_played += 1
                    if match.winner_id == our_player.id:
                        m.matches_won += 1

        result = list(agg.values())
        result.sort(key=lambda x: (-x.matches_played, -x.winrate, x.opponent_commander.lower()))
        return result

    def get_commander_highlights(self, format_name: str) -> dict:
        """
        Retourne le commandant le plus joué et le plus victorieux pour un format donné.
        Retourne {"most_played": (name, count) | None, "most_wins": (name, count) | None}
        """
        play_count: dict[str, int] = defaultdict(int)
        win_count: dict[str, int] = defaultdict(int)

        for tournament in self._tournaments:
            if tournament.format != format_name:
                continue

            players_by_id = {p.id: p for p in tournament.players}

            if tournament.is_1v1_format():
                standings = build_standings(tournament)
                swiss_ordered = [players_by_id[e.player_id] for e in standings if e.player_id in players_by_id]
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

            for rank, player in enumerate(ranked, 1):
                if not player.commander:
                    continue
                cmd = player.commander
                play_count[cmd] += 1
                if rank == 1:
                    win_count[cmd] += 1

        most_played = None
        if play_count:
            name = max(play_count, key=play_count.get)
            most_played = (name, play_count[name])

        most_wins = None
        if win_count:
            name = max(win_count, key=win_count.get)
            most_wins = (name, win_count[name])

        return {"most_played": most_played, "most_wins": most_wins}

    def get_head_to_head(self, player_name: str, opponent_name: str) -> MatchupStats | None:
        """Retourne les stats détaillées entre deux joueurs."""
        matchups = self.get_player_matchups(player_name)
        opponent_key = self._normalize_name(opponent_name)

        for matchup in matchups:
            if self._normalize_name(matchup.opponent_name) == opponent_key:
                return matchup

        return None
