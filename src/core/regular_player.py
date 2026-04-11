from dataclasses import dataclass


@dataclass
class RegularPlayer:
    """
    Joueur régulier inscrit dans le système.
    Différent de Player qui est spécifique à un tournoi.
    """

    id: int
    pseudo: str
    full_name: str = ""
    phone: str = ""
    discord_id: str = ""
    discord_pseudo: str = ""
    top_1: int = 0
    top_2: int = 0
    top_3: int = 0
    points: int = 0
    tournaments_played: int = 0

    def add_top(self, position: int) -> None:
        """Ajoute un podium au joueur."""
        if position == 1:
            self.top_1 += 1
        elif position == 2:
            self.top_2 += 1
        elif position == 3:
            self.top_3 += 1

    def add_points(self, value: int) -> None:
        """Ajoute des points de participation."""
        self.points += value

    @property
    def total_podiums(self) -> int:
        """Nombre total de podiums."""
        return self.top_1 + self.top_2 + self.top_3

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pseudo": self.pseudo,
            "full_name": self.full_name,
            "phone": self.phone,
            "discord_id": self.discord_id,
            "discord_pseudo": self.discord_pseudo,
            "top_1": self.top_1,
            "top_2": self.top_2,
            "top_3": self.top_3,
            "points": self.points,
            "tournaments_played": self.tournaments_played,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RegularPlayer":
        return cls(
            id=data["id"],
            pseudo=data["pseudo"],
            full_name=data.get("full_name", ""),
            phone=data.get("phone", ""),
            discord_id=str(data.get("discord_id") or ""),
            discord_pseudo=str(data.get("discord_pseudo") or ""),
            top_1=data.get("top_1", 0),
            top_2=data.get("top_2", 0),
            top_3=data.get("top_3", 0),
            points=data.get("points", 0),
            tournaments_played=data.get("tournaments_played", 0),
        )
