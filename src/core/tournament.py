from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict
from core.player import Player
from core.round import Round
from core.table import Table
import random

@dataclass
class Tournament:
    id: int
    name: str
    format: str
    date: str

    players: list[Player] = field(default_factory=list)
    rounds: list[Round] = field(default_factory=list)

    _next_player_id: int = 0

    # =====================
    # Business logic
    # =====================


    ### PLAYER
    @staticmethod
    def create_tournament(*, tournament_id: int, name: str, format: str, date: str) -> "Tournament":
        return Tournament(
            id=tournament_id,
            name=name.strip(),
            format=format.strip(),
            date=date,
            players=[],
        )

    def add_player(self, name: str) -> Player | None:
        name = name.strip()
        if not name:
            return None

        # Empêcher les doublons (case-insensitive)
        if any(p.name.lower() == name.lower() for p in self.players):
            return None

        player = Player(
            id=self._next_player_id,
            name=name,
        )
        self.players.append(player)
        self._next_player_id += 1
        return player

    def remove_player(self, player_id: int) -> None:
        self.players = [
            p for p in self.players
            if p.id != player_id
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
    def create_round(self) -> Round:
        round_number = len(self.rounds) + 1
        tables = self._generate_tables()

        new_round = Round(
            number=round_number,
            tables=tables
        )

        self.rounds.append(new_round)
        return new_round

    def _generate_tables(self) -> list[Table] | None:
        """
        Génère les tables à partir des scores et de la robustesse.
        """
        player_count = len(self.players)

        table_sizes = self.compute_table_sizes(player_count)

        if table_sizes is None:
            return None

        ordered_players = self.sort_players()

        tables: list[Table] = []
        index = 0
        table_number = 1

        for size in table_sizes:
            table_players = ordered_players[index:index + size]

            tables.append(
                Table(
                    number=table_number,
                    players=table_players
                )
            )

            index += size
            table_number += 1

        return tables

    def compute_table_sizes(self, player_count: int) -> list[int] | None:
        """
        Retourne une liste de tailles de tables (4 ou 3),
        ou None si impossible.
        """
        if self.format == "👑 Commander":
            if player_count < 6:
                return None

            sizes: list[int] = []

            max_fours = player_count // 4

            for fours in range(max_fours, -1, -1):
                remaining = player_count - 4 * fours

                if remaining == 0:
                    sizes = [4] * fours
                    return sizes

                if remaining % 3 == 0:
                    threes = remaining // 3
                    if threes > 0:
                        sizes = [4] * fours + [3] * threes
                        return sizes

            return None

        else:
            if player_count < 4:
                return None  

            table_count = player_count // 2
            return [2] * table_count

    def sort_players(self) -> list[Player]:
        """
        Trie les joueurs selon les règles métier.
        """
        if all(p.score == 0 for p in self.players):
            shuffled = self.players[:]
            random.shuffle(shuffled)
            return shuffled

        return sorted(
            self.players,
            key=lambda p: (p.score, p.robustness),
            reverse=True
        )

    def update(self, *, name: str, format: str, date: str) -> None:
        self.name = name.strip()
        self.format = format.strip()
        self.date = date

    @property
    def player_count(self) -> int:
        return len(self.players)

    # =====================
    # Tables
    # =====================

    def table_count(self) -> int | None:
        n = self.player_count

        # COMMANDER
        if self.format == "👑 Commander":
            if n < 6:
                return None

            max_fours = n // 4
            for fours in range(max_fours, -1, -1):
                remainder = n - 4 * fours
                if remainder == 0:
                    return fours
                if remainder % 3 == 0:
                    return fours + remainder // 3

            return None

        # AUTRES FORMATS (tables de 2)
        if n < 4:
            return None

        return n // 2

    # =====================
    # Serialization
    # =====================

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "format": self.format,
            "date": self.date,
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "score": p.score,
                    "robustness": p.robustness,
                }
                for p in self.players
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "Tournament":
        tournament = cls(
            id=data["id"],
            name=data["name"],
            format=data["format"],
            date=data["date"],
            players=[],
        )

        for p in data.get("players", []):
            player = Player(
                id=p["id"],
                name=p["name"],
                score=p.get("score", 0),
                robustness=p.get("robustness", 0),
            )
            tournament.players.append(player)
            tournament._next_player_id = max(
                tournament._next_player_id,
                player.id + 1
            )

        return tournament


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
