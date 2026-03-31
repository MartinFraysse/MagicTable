"""
Tests unitaires pour le module core.standings.

Couvre :
- Scoring basique (Win=3, Draw=1, Loss=0)
- MW% calculation
- OMW% avec floor 0.33
- Bye handling
- Match non joué (ignoré)
- Cas 0 match joué (MW% = 0.0)
- Tri correct des standings
"""

import sys
import os

# Ajouter src/ au path pour les imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from core.player import Player
from core.table import Table
from core.round import Round, RoundState
from core.tournament import Tournament
from core.standings import build_standings, StandingEntry


def _make_tournament(players: list[Player], rounds: list[Round]) -> Tournament:
    """Helper pour créer un tournoi de test."""
    return Tournament(
        id=1,
        name="Test",
        format="⚔️ Duel Commander",
        date="01/01/2026",
        players=players,
        rounds=rounds,
    )


def _make_finished_table(number: int, p1: Player, p2: Player, winner_id: int) -> Table:
    """Crée une table 1v1 terminée. Le winner obtient position 1, l'autre position 3."""
    other_id = p2.id if winner_id == p1.id else p1.id
    return Table(
        number=number,
        players=[p1, p2],
        finished=True,
        results={winner_id: 1, other_id: 3},
    )


def _make_bye_table(number: int, player: Player) -> Table:
    """Crée une table bye terminée."""
    return Table(
        number=number,
        players=[player],
        finished=True,
        results={player.id: 1},
    )


def _find(standings: list[StandingEntry], player_id: int) -> StandingEntry:
    """Trouve un StandingEntry par player_id."""
    for e in standings:
        if e.player_id == player_id:
            return e
    raise ValueError(f"Player {player_id} not found in standings")


# =====================================================================
# Tests
# =====================================================================

class TestBasicScoring:
    """Scoring Win=3, Loss=0."""

    def test_single_match_winner_gets_3(self):
        p1 = Player(id=0, name="Alice")
        p2 = Player(id=1, name="Bob")
        t1 = _make_finished_table(1, p1, p2, winner_id=0)
        r1 = Round(number=1, tables=[t1], state=RoundState.FINISHED)
        tournament = _make_tournament([p1, p2], [r1])

        standings = build_standings(tournament)
        alice = _find(standings, 0)
        bob = _find(standings, 1)

        assert alice.match_points == 3
        assert alice.wins == 1
        assert alice.losses == 0
        assert alice.draws == 0

        assert bob.match_points == 0
        assert bob.wins == 0
        assert bob.losses == 1

    def test_two_rounds(self):
        p1 = Player(id=0, name="Alice")
        p2 = Player(id=1, name="Bob")

        # Round 1: Alice gagne
        t1 = _make_finished_table(1, p1, p2, winner_id=0)
        r1 = Round(number=1, tables=[t1], state=RoundState.FINISHED)

        # Round 2: Bob gagne
        t2 = _make_finished_table(1, p1, p2, winner_id=1)
        r2 = Round(number=2, tables=[t2], state=RoundState.FINISHED)

        tournament = _make_tournament([p1, p2], [r1, r2])
        standings = build_standings(tournament)

        alice = _find(standings, 0)
        bob = _find(standings, 1)

        # Chacun a 1 victoire et 1 défaite
        assert alice.match_points == 3
        assert bob.match_points == 3
        assert alice.wins == 1 and alice.losses == 1
        assert bob.wins == 1 and bob.losses == 1


class TestMWPercent:
    """Match Win Percentage = match_points / (3 * matches_played)."""

    def test_100_percent(self):
        p1 = Player(id=0, name="Alice")
        p2 = Player(id=1, name="Bob")
        t1 = _make_finished_table(1, p1, p2, winner_id=0)
        r1 = Round(number=1, tables=[t1], state=RoundState.FINISHED)
        tournament = _make_tournament([p1, p2], [r1])

        standings = build_standings(tournament)
        alice = _find(standings, 0)

        # 3 / (3 * 1) = 1.0
        assert abs(alice.mw_pct - 1.0) < 1e-9

    def test_0_percent(self):
        p1 = Player(id=0, name="Alice")
        p2 = Player(id=1, name="Bob")
        t1 = _make_finished_table(1, p1, p2, winner_id=0)
        r1 = Round(number=1, tables=[t1], state=RoundState.FINISHED)
        tournament = _make_tournament([p1, p2], [r1])

        standings = build_standings(tournament)
        bob = _find(standings, 1)

        # 0 / (3 * 1) = 0.0
        assert abs(bob.mw_pct - 0.0) < 1e-9

    def test_50_percent(self):
        p1 = Player(id=0, name="Alice")
        p2 = Player(id=1, name="Bob")

        t1 = _make_finished_table(1, p1, p2, winner_id=0)
        r1 = Round(number=1, tables=[t1], state=RoundState.FINISHED)

        t2 = _make_finished_table(1, p1, p2, winner_id=1)
        r2 = Round(number=2, tables=[t2], state=RoundState.FINISHED)

        tournament = _make_tournament([p1, p2], [r1, r2])
        standings = build_standings(tournament)

        alice = _find(standings, 0)
        # 3 / (3 * 2) = 0.5
        assert abs(alice.mw_pct - 0.5) < 1e-9

    def test_no_matches_played(self):
        p1 = Player(id=0, name="Alice")
        tournament = _make_tournament([p1], [])

        standings = build_standings(tournament)
        alice = _find(standings, 0)

        assert alice.mw_pct == 0.0
        assert alice.matches_played == 0


class TestOMWPercent:
    """Opponent Match Win % avec floor 0.33."""

    def test_omw_with_strong_opponent(self):
        """Alice bat Bob, Bob bat Charlie. L'adversaire d'Alice (Bob) a 50% MW."""
        p1 = Player(id=0, name="Alice")
        p2 = Player(id=1, name="Bob")
        p3 = Player(id=2, name="Charlie")

        # Round 1: Alice bat Bob, Charlie bye
        t1 = _make_finished_table(1, p1, p2, winner_id=0)
        r1 = Round(number=1, tables=[t1], state=RoundState.FINISHED)

        # Round 2: Bob bat Charlie, Alice bye
        t2 = _make_finished_table(1, p2, p3, winner_id=1)
        r2 = Round(number=2, tables=[t2], state=RoundState.FINISHED)

        tournament = _make_tournament([p1, p2, p3], [r1, r2])
        standings = build_standings(tournament)

        alice = _find(standings, 0)
        bob = _find(standings, 1)

        # Bob: 1W 1L -> MW% = 3/(3*2) = 0.5
        assert abs(bob.mw_pct - 0.5) < 1e-9

        # Alice a un seul adversaire: Bob (MW% = 0.5)
        # OMW% = max(0.5, 0.33) = 0.5
        assert abs(alice.omw_pct - 0.5) < 1e-9

    def test_omw_floor_033(self):
        """Le floor 0.33 s'applique quand l'adversaire a 0% MW."""
        p1 = Player(id=0, name="Alice")
        p2 = Player(id=1, name="Bob")

        # Alice bat Bob (seul match)
        t1 = _make_finished_table(1, p1, p2, winner_id=0)
        r1 = Round(number=1, tables=[t1], state=RoundState.FINISHED)

        tournament = _make_tournament([p1, p2], [r1])
        standings = build_standings(tournament)

        alice = _find(standings, 0)

        # Bob a 0% MW, floor à 0.33
        # OMW%(Alice) = max(0.0, 0.33) = 0.33
        assert abs(alice.omw_pct - 0.33) < 1e-9

    def test_omw_no_opponents(self):
        """Un joueur sans adversaire a OMW% = 0.0."""
        p1 = Player(id=0, name="Alice")
        tournament = _make_tournament([p1], [])

        standings = build_standings(tournament)
        alice = _find(standings, 0)

        assert alice.omw_pct == 0.0

    def test_omw_multiple_opponents(self):
        """OMW% est la moyenne des MW% adverses (avec floor)."""
        p1 = Player(id=0, name="Alice")
        p2 = Player(id=1, name="Bob")
        p3 = Player(id=2, name="Charlie")

        # Round 1: Alice bat Bob
        t1 = _make_finished_table(1, p1, p2, winner_id=0)
        # Round 2: Alice bat Charlie
        t2 = _make_finished_table(1, p1, p3, winner_id=0)

        r1 = Round(number=1, tables=[t1], state=RoundState.FINISHED)
        r2 = Round(number=2, tables=[t2], state=RoundState.FINISHED)

        tournament = _make_tournament([p1, p2, p3], [r1, r2])
        standings = build_standings(tournament)

        alice = _find(standings, 0)

        # Bob: 0W 1L -> MW% = 0.0, floor -> 0.33
        # Charlie: 0W 1L -> MW% = 0.0, floor -> 0.33
        # OMW%(Alice) = (0.33 + 0.33) / 2 = 0.33
        assert abs(alice.omw_pct - 0.33) < 1e-9


class TestByeHandling:
    """Bye = Win (3 pts), mais pas d'adversaire pour OMW/OGW."""

    def test_bye_gives_3_points(self):
        p1 = Player(id=0, name="Alice")
        bye_table = _make_bye_table(1, p1)
        r1 = Round(number=1, tables=[bye_table], state=RoundState.FINISHED)

        tournament = _make_tournament([p1], [r1])
        standings = build_standings(tournament)

        alice = _find(standings, 0)
        assert alice.match_points == 3
        assert alice.wins == 1
        assert alice.matches_played == 1

    def test_bye_no_opponent_for_omw(self):
        p1 = Player(id=0, name="Alice")
        bye_table = _make_bye_table(1, p1)
        r1 = Round(number=1, tables=[bye_table], state=RoundState.FINISHED)

        tournament = _make_tournament([p1], [r1])
        standings = build_standings(tournament)

        alice = _find(standings, 0)
        # Pas d'adversaire → OMW% = 0.0
        assert alice.omw_pct == 0.0

    def test_bye_plus_real_match(self):
        """Un joueur avec bye + match réel."""
        p1 = Player(id=0, name="Alice")
        p2 = Player(id=1, name="Bob")

        # Round 1: Alice a un bye
        bye_table = _make_bye_table(1, p1)
        # Bob ne joue pas ce round (impair)
        r1 = Round(number=1, tables=[bye_table], state=RoundState.FINISHED)

        # Round 2: Alice bat Bob
        t2 = _make_finished_table(1, p1, p2, winner_id=0)
        r2 = Round(number=2, tables=[t2], state=RoundState.FINISHED)

        tournament = _make_tournament([p1, p2], [r1, r2])
        standings = build_standings(tournament)

        alice = _find(standings, 0)
        assert alice.match_points == 6  # 3 (bye) + 3 (win)
        assert alice.wins == 2
        assert alice.matches_played == 2
        # MW% = 6 / (3*2) = 1.0
        assert abs(alice.mw_pct - 1.0) < 1e-9

        # OMW% : seul adversaire est Bob (0 wins, 1 loss -> MW% = 0.0, floor 0.33)
        assert abs(alice.omw_pct - 0.33) < 1e-9


class TestUnplayedMatch:
    """Les tables non terminées sont ignorées."""

    def test_unfinished_table_ignored(self):
        p1 = Player(id=0, name="Alice")
        p2 = Player(id=1, name="Bob")

        # Table non terminée
        unfinished = Table(
            number=1,
            players=[p1, p2],
            finished=False,
            results={},
        )
        r1 = Round(number=1, tables=[unfinished], state=RoundState.IN_PROGRESS)

        tournament = _make_tournament([p1, p2], [r1])
        standings = build_standings(tournament)

        alice = _find(standings, 0)
        assert alice.match_points == 0
        assert alice.matches_played == 0

    def test_missing_result_ignored(self):
        """Table terminée mais résultat manquant pour un joueur."""
        p1 = Player(id=0, name="Alice")
        p2 = Player(id=1, name="Bob")

        # Table terminée mais résultat partiel
        partial = Table(
            number=1,
            players=[p1, p2],
            finished=True,
            results={0: 1},  # Bob n'a pas de résultat
        )
        r1 = Round(number=1, tables=[partial], state=RoundState.FINISHED)

        tournament = _make_tournament([p1, p2], [r1])
        standings = build_standings(tournament)

        alice = _find(standings, 0)
        bob = _find(standings, 1)
        # Résultat incomplet → ignoré
        assert alice.matches_played == 0
        assert bob.matches_played == 0


class TestSortOrder:
    """Tri : match_points DESC, OMW% DESC, name ASC."""

    def test_sort_by_points(self):
        p1 = Player(id=0, name="Alice")
        p2 = Player(id=1, name="Bob")

        t1 = _make_finished_table(1, p1, p2, winner_id=0)
        r1 = Round(number=1, tables=[t1], state=RoundState.FINISHED)

        tournament = _make_tournament([p1, p2], [r1])
        standings = build_standings(tournament)

        # Alice (3 pts) doit être avant Bob (0 pts)
        assert standings[0].player_id == 0
        assert standings[1].player_id == 1

    def test_sort_by_omw_when_tied(self):
        """A et B ont les mêmes points, départagés par OMW%."""
        p1 = Player(id=0, name="Alice")
        p2 = Player(id=1, name="Bob")
        p3 = Player(id=2, name="Charlie")
        p4 = Player(id=3, name="Diana")

        # Round 1: Alice bat Charlie, Bob bat Diana
        t1 = _make_finished_table(1, p1, p3, winner_id=0)
        t2 = _make_finished_table(2, p2, p4, winner_id=1)
        r1 = Round(number=1, tables=[t1, t2], state=RoundState.FINISHED)

        # Round 2: Charlie bat Diana (donne de la force à Charlie, adversaire d'Alice)
        t3 = _make_finished_table(1, p3, p4, winner_id=2)
        # Alice et Bob ne jouent pas ce round (ou jouent entre eux)
        r2 = Round(number=2, tables=[t3], state=RoundState.FINISHED)

        tournament = _make_tournament([p1, p2, p3, p4], [r1, r2])
        standings = build_standings(tournament)

        alice = _find(standings, 0)
        bob = _find(standings, 1)

        # Alice et Bob ont chacun 3 pts (1 win)
        assert alice.match_points == 3
        assert bob.match_points == 3

        # Charlie (adversaire d'Alice) : 1W 1L -> MW% = 0.5 -> contrib = 0.5
        # Diana (adversaire de Bob) : 0W 2L -> MW% = 0.0 -> contrib = 0.33
        # OMW%(Alice) = 0.5 > OMW%(Bob) = 0.33
        assert alice.omw_pct > bob.omw_pct

        # Alice doit être classée avant Bob
        alice_rank = next(i for i, e in enumerate(standings) if e.player_id == 0)
        bob_rank = next(i for i, e in enumerate(standings) if e.player_id == 1)
        assert alice_rank < bob_rank

    def test_sort_by_name_as_tiebreaker(self):
        """Départage final par nom alphabétique."""
        p1 = Player(id=0, name="Bob")
        p2 = Player(id=1, name="Alice")

        # Aucun match joué → tous à 0 pts, 0 OMW%
        tournament = _make_tournament([p1, p2], [])
        standings = build_standings(tournament)

        # Alice doit être avant Bob (alphabétique)
        assert standings[0].player_name == "Alice"
        assert standings[1].player_name == "Bob"


class TestGWPlaceholder:
    """GW% et OGW% sont des placeholders à 0.0."""

    def test_gw_and_ogw_are_zero(self):
        p1 = Player(id=0, name="Alice")
        p2 = Player(id=1, name="Bob")

        t1 = _make_finished_table(1, p1, p2, winner_id=0)
        r1 = Round(number=1, tables=[t1], state=RoundState.FINISHED)

        tournament = _make_tournament([p1, p2], [r1])
        standings = build_standings(tournament)

        for entry in standings:
            assert entry.gw_pct == 0.0
            assert entry.ogw_pct == 0.0
