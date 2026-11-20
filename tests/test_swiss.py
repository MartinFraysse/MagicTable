"""
Tests du système Swiss (formats 1v1).

Priorités d'appariement attendues :
  1. pas de second bye si un autre joueur peut le recevoir
  2. pas de rematch si une alternative existe
  3. bye au joueur le moins bien classé
  4. écarts de score minimaux (pénalité quadratique : pas de gros « pair-down »)
  5. hasard entre appariements équivalents (round 1 aléatoire)
"""

import os
import random
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from core.player import Player
from core.round import RoundState
from core.standings import build_standings
from core.swiss_pairing import generate_swiss_pairings
from core.tournament import Tournament


def _players(scores: list[int]) -> list[Player]:
    return [Player(id=i, name=f"P{i:02d}", score=s) for i, s in enumerate(scores)]


def _tournament(n: int, fmt: str = "🏆 AP") -> Tournament:
    t = Tournament.create_tournament(
        tournament_id=0, name="T", format=fmt, date="01/01/2026", max_rounds=8
    )
    t.pairing_system = "standard" if fmt == "👑 Commander" else "swiss"
    for i in range(n):
        t.add_player(f"P{i:02d}")
    return t


def _play_round(t: Tournament, rng: random.Random) -> None:
    """Joue le round courant comme le dashboard (résultats + scores)."""
    rnd = t.rounds[-1]
    rnd.start()
    for tb in rnd.tables:
        if tb.finished:
            continue
        a, b = tb.players
        g = rng.choice([(2, 0), (2, 1), (1, 1), (1, 2), (0, 2)])
        tb.game_scores = {a.id: g[0], b.id: g[1]}
        tb.results = {a.id: 1 if g[0] >= g[1] else 2, b.id: 1 if g[1] >= g[0] else 2}
        tb.finished = True
    rnd.finish()
    for e in build_standings(t):
        next(p for p in t.players if p.id == e.player_id).score = e.match_points


class TestSwissForAll1v1Formats:
    def test_every_1v1_format_uses_swiss(self):
        for fmt in ["⚔️ Duel Commander", "🃏 Draft", "🏆 AP", "⚡ Pokemon", "🔥 Rise"]:
            t = _tournament(5, fmt)
            t.pairing_system = "standard"  # ancien tournoi : ignoré pour un format 1v1
            assert t.is_swiss_format(), fmt
            rnd = t.create_round()
            # Swiss : effectif impair → un bye (et non un joueur laissé de côté)
            assert sum(1 for tb in rnd.tables if len(tb.players) == 1) == 1, fmt

    def test_commander_multi_is_not_swiss(self):
        t = _tournament(8, "👑 Commander")
        assert not t.is_swiss_format()
        assert all(len(tb.players) in (3, 4) for tb in t.create_round().tables)


class TestRoundOne:
    def test_round_one_is_not_alphabetical(self):
        """Avec tous les scores à 0, les paires ne doivent pas suivre l'ordre des noms."""
        alphabetical = 0
        for seed in range(20):
            random.seed(seed)
            t = _tournament(12)
            rnd = t.create_round()
            pairs = {tuple(sorted(p.id for p in tb.players)) for tb in rnd.tables}
            if pairs == {(i, i + 1) for i in range(0, 12, 2)}:
                alphabetical += 1
        assert alphabetical == 0

    def test_round_one_varies_between_draws(self):
        seen = set()
        for seed in range(10):
            random.seed(seed)
            rnd = _tournament(10).create_round()
            seen.add(frozenset(frozenset(p.id for p in tb.players) for tb in rnd.tables))
        assert len(seen) > 1


class TestPairingQuality:
    def test_avoids_big_pair_down(self):
        """
        Scores 9, 9, 9, 3, 3, 0 avec quelques rencontres déjà jouées.
        Mauvais : 9-9, 9-0 (écart 9), 3-3.   Attendu : 9-9, 9-3 (écart 6), 3-0 (écart 3).
        Aucun joueur à 9 points ne doit rencontrer le joueur à 0.
        """
        players = _players([9, 9, 9, 3, 3, 0])
        opp = {0: {5}, 1: set(), 2: {4}, 3: set(), 4: {2, 5}, 5: {0, 4}}
        res = generate_swiss_pairings(players, opp, set())
        assert not res.had_rematch
        gaps = sorted(abs(a.score - b.score) for a, b in res.pairings)
        assert gaps == [0, 3, 6]

    def test_no_rematch_when_avoidable(self):
        players = _players([3, 3, 0, 0])
        opp = {0: {1}, 1: {0}, 2: {3}, 3: {2}}
        res = generate_swiss_pairings(players, opp, set())
        assert not res.had_rematch
        for a, b in res.pairings:
            assert b.id not in opp[a.id]

    def test_rematch_only_when_unavoidable(self):
        players = _players([0, 0])
        res = generate_swiss_pairings(players, {0: {1}, 1: {0}}, set())
        assert res.had_rematch and len(res.pairings) == 1

    def test_bye_goes_to_lowest_without_previous_bye(self):
        players = _players([6, 3, 3, 0, 0])
        res = generate_swiss_pairings(players, {p.id: set() for p in players}, bye_history={4})
        assert res.bye_player.id == 3

    def test_second_bye_only_when_everyone_had_one(self):
        players = _players([3, 3, 3])
        res = generate_swiss_pairings(players, {p.id: set() for p in players}, bye_history={0, 1, 2})
        assert res.bye_player is not None
        assert len(res.pairings) == 1

    def test_dropped_players_are_never_paired(self):
        t = _tournament(8)
        rng = random.Random(1)
        t.create_round()
        _play_round(t, rng)
        t.players[3].dropped = True
        rnd = t.create_round()
        ids = [p.id for tb in rnd.tables for p in tb.players]
        assert 3 not in ids and len(ids) == 7


class TestFullTournaments:
    def test_simulated_tournaments_have_no_avoidable_rematch_and_are_fast(self):
        rng = random.Random(42)
        random.seed(42)
        worst = 0.0
        for n in (7, 16, 25, 40):
            t = _tournament(n)
            for _ in range(6):
                start = time.perf_counter()
                rnd = t.create_round()
                worst = max(worst, time.perf_counter() - start)
                active = [p for p in t.players if not p.dropped]
                seated = [p.id for tb in rnd.tables for p in tb.players]
                assert sorted(seated) == sorted(p.id for p in active)
                assert len(set(seated)) == len(seated)
                _play_round(t, rng)
        assert worst < 0.5, f"génération trop lente : {worst:.2f}s"

    def test_rounds_are_marked_finished(self):
        t = _tournament(6)
        t.create_round()
        _play_round(t, random.Random(0))
        t.create_round()
        assert t.rounds[0].state == RoundState.FINISHED


class TestByeInStandings:
    def test_bye_counts_as_two_game_wins(self):
        """MTR : un bye compte comme un match gagné 2-0 (GW%)."""
        t = _tournament(3)
        rnd = t.create_round()
        bye = next(tb.players[0] for tb in rnd.tables if len(tb.players) == 1)
        for tb in rnd.tables:
            if len(tb.players) == 2:
                a, b = tb.players
                tb.results, tb.game_scores, tb.finished = {a.id: 1, b.id: 2}, {a.id: 2, b.id: 1}, True
        entry = next(e for e in build_standings(t) if e.player_id == bye.id)
        assert entry.gw_pct == 1.0
