from core.regular_player import RegularPlayer
from storage.base import JsonStorage


class RegularPlayerStorage(JsonStorage):
    filename = "regular_players.json"

    @classmethod
    def load_players(cls) -> list[RegularPlayer]:
        return [RegularPlayer.from_dict(d) for d in cls.load()]

    @classmethod
    def save_players(cls, players: list[RegularPlayer]) -> None:
        cls.save([p.to_dict() for p in players])

    @classmethod
    def add_player(cls, pseudo: str) -> RegularPlayer | None:
        """
        Crée un joueur régulier et le sauvegarde.
        Retourne None si un joueur avec ce pseudo (insensible à la casse) existe déjà.
        """
        players = cls.load_players()
        key = pseudo.lower().strip()
        if any(p.pseudo.lower().strip() == key for p in players):
            return None

        new_player = RegularPlayer(
            id=max((p.id for p in players), default=0) + 1,
            pseudo=pseudo.strip(),
        )
        players.append(new_player)
        cls.save_players(players)
        return new_player
