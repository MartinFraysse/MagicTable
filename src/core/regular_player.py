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

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pseudo": self.pseudo,
            "full_name": self.full_name,
            "phone": self.phone,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "RegularPlayer":
        return cls(
            id=data["id"],
            pseudo=data["pseudo"],
            full_name=data.get("full_name", ""),
            phone=data.get("phone", ""),
        )
