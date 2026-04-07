from dataclasses import dataclass


@dataclass
class CommanderPlayer:
    """
    Joueur régulier de format Commander.
    Différent de RegularPlayer qui est pour les formats 1v1.
    """

    id: int
    pseudo: str
    full_name: str = ""
    phone: str = ""
    top_1: int = 0
    top_2: int = 0
    top_3: int = 0
    top_4: int = 0
    points: int = 0
    tournaments_played: int = 0

    def add_top(self, position: int) -> None:
        """Ajoute un résultat de position au joueur."""
        if position == 1:
            self.top_1 += 1
        elif position == 2:
            self.top_2 += 1
        elif position == 3:
            self.top_3 += 1
        elif position == 4:
            self.top_4 += 1

    @property
    def total_podiums(self) -> int:
        """Nombre total de podiums (top 3)."""
        return self.top_1 + self.top_2 + self.top_3

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pseudo": self.pseudo,
            "full_name": self.full_name,
            "phone": self.phone,
            "top_1": self.top_1,
            "top_2": self.top_2,
            "top_3": self.top_3,
            "top_4": self.top_4,
            "points": self.points,
            "tournaments_played": self.tournaments_played,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CommanderPlayer":
        return cls(
            id=data["id"],
            pseudo=data["pseudo"],
            full_name=data.get("full_name", ""),
            phone=data.get("phone", ""),
            top_1=data.get("top_1", 0),
            top_2=data.get("top_2", 0),
            top_3=data.get("top_3", 0),
            top_4=data.get("top_4", 0),
            points=data.get("points", 0),
            tournaments_played=data.get("tournaments_played", 0),
        )
