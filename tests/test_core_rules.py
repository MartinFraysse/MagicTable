"""
Tests des règles métier corrigées lors du nettoyage :
- bracket : les slots vides ne donnent la victoire que s'ils ne seront plus remplis
- byes Swiss : l'historique suit les rounds existants
- stats des joueurs réguliers : source unique (archives), lien explicite ou pseudo
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from core.bracket import Bracket, BracketType, create_bracket_matches
from core.regular_player import RegularPlayer
from core.stats_analyzer import StatsAnalyzer
from core.tournament import Tournament


def _bracket(bracket_type: BracketType, seeds: list[int]) -> Bracket:
    b = Bracket(bracket_type=bracket_type, matches=create_bracket_matches(bracket_type, seeds))
    b.auto_resolve_dropped(set())
    return b


def _match(b: Bracket, match_id: int):
    return next(m for m in b.matches if m.match_id == match_id)


class TestBracketMissingSeeds:
    def test_top8_with_7_players_seed1_does_not_win_final_for_free(self):
        b = _bracket(BracketType.QUART_DE_FINALE, [1, 2, 3, 4, 5, 6, 7])
        assert _match(b, 0).winner_id == 1          # 1 vs (vide) → bye
        assert not _match(b, 4).finished            # demi : attend le vainqueur de 4v5
        assert not _match(b, 7).finished            # finale non attribuée
        assert not b.finished

    def test_top4_with_3_players_full_flow(self):
        b = _bracket(BracketType.DEMI_FINALE, [1, 2, 3])
        assert not _match(b, 3).finished            # finale en attente
        b.record_result(1, 2)                       # 2 bat 3
        b.auto_resolve_dropped(set())
        assert (_match(b, 3).player1_id, _match(b, 3).player2_id) == (1, 2)
        assert _match(b, 2).winner_id == 3          # petite finale : 3 seul → 3e
        b.record_result(3, 1)
        assert b.finished

    def test_top4_with_2_players_petite_finale_closed(self):
        b = _bracket(BracketType.DEMI_FINALE, [1, 2])
        petite = _match(b, 2)
        assert petite.finished and petite.winner_id is None
        b.record_result(3, 2)
        assert b.finished

    def test_drop_outside_bracket_does_not_resolve_waiting_final(self):
        b = _bracket(BracketType.DEMI_FINALE, [1, 2, 3, 4])
        b.record_result(0, 1)
        assert b.auto_resolve_dropped({99}) == []
        assert not _match(b, 3).finished

    def test_drop_inside_bracket_gives_forfeit(self):
        b = _bracket(BracketType.DEMI_FINALE, [1, 2, 3, 4])
        b.record_result(0, 1)                       # 1 bat 4
        b.auto_resolve_dropped({3})                 # 3 abandonne en demi 2
        assert _match(b, 1).winner_id == 2
        assert _match(b, 2).winner_id == 4          # petite finale : 4 vs 3 (droppé)


class TestByeHistory:
    def _swiss(self, n: int) -> Tournament:
        t = Tournament.create_tournament(
            tournament_id=0, name="T", format="🏆 AP", date="01/01/2026", max_rounds=3
        )
        t.pairing_system = "swiss"
        for i in range(n):
            t.add_player(f"P{i}")
        return t

    def test_bye_recorded_on_round_creation(self):
        t = self._swiss(5)
        t.create_round_swiss()
        assert len(t.bye_history) == 1
        assert sum(p.had_bye for p in t.players) == 1

    def test_bye_released_when_preparation_round_invalidated(self):
        t = self._swiss(5)
        t.create_round_swiss()
        t.add_player("Retardataire")                # invalide le round en préparation
        assert t.rounds == []
        assert t.bye_history == set()
        assert not any(p.had_bye for p in t.players)

    def test_bye_history_survives_serialization(self):
        t = self._swiss(5)
        t.create_round_swiss()
        restored = Tournament.from_dict(t.to_dict())
        restored.sync_byes()
        assert restored.bye_history == t.bye_history


class TestRegularPlayerStats:
    def _archived(self, tid: int, players: list[tuple[str, int | None, int]]) -> Tournament:
        """players : (nom, regular_player_id, score). Commander → classement par score."""
        t = Tournament.create_tournament(
            tournament_id=tid, name=f"T{tid}", format="👑 Commander", date="01/01/2026"
        )
        for name, rp_id, score in players:
            p = t.add_player(name, regular_player_id=rp_id)
            p.score = score
        t.archived = True
        return t

    def test_explicit_link_and_pseudo_fallback(self):
        regulars = [RegularPlayer(id=1, pseudo="Alice"), RegularPlayer(id=2, pseudo="Bob")]
        tournaments = [
            # Ancien tournoi : pas de lien → rattachement par pseudo
            self._archived(0, [("alice", None, 9), ("Bob", None, 6), ("Zoé", None, 3)]),
            # Nouveau tournoi : lien explicite, même si le nom diffère
            self._archived(1, [("Bobby", 2, 9), ("Alice", 1, 6), ("Zoé", None, 3)]),
        ]
        sa = StatsAnalyzer(tournaments, regular_players=regulars)

        alice = sa.get_regular_player_stats(1)
        bob = sa.get_regular_player_stats(2)
        assert (alice.tournaments_played, alice.total_points, alice.top_1, alice.top_2) == (2, 15, 1, 1)
        assert (bob.tournaments_played, bob.total_points, bob.top_1, bob.top_2) == (2, 15, 1, 1)

        ranking = sa.get_regular_players_ranking()
        assert {s.name for s in ranking} == {"Alice", "Bob"}   # Zoé n'est pas régulière

    def test_link_to_deleted_regular_is_not_matched_by_pseudo(self):
        regulars = [RegularPlayer(id=1, pseudo="Alice")]
        tournaments = [self._archived(0, [("Alice", 42, 9), ("X", None, 1), ("Y", None, 0)])]
        sa = StatsAnalyzer(tournaments, regular_players=regulars)
        assert sa.get_regular_player_stats(1).tournaments_played == 0

    def test_unknown_regular_returns_zero_stats(self):
        sa = StatsAnalyzer([], regular_players=[])
        assert sa.get_regular_player_stats(123).tournaments_played == 0
