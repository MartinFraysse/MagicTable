from dataclasses import dataclass, field


MTG_COLORS = ["W", "U", "B", "R", "G"]

COLOR_LABELS = {
    "W": "Blanc",
    "U": "Bleu",
    "B": "Noir",
    "R": "Rouge",
    "G": "Vert",
}

COLOR_SYMBOLS = {
    "W": "☀",
    "U": "💧",
    "B": "💀",
    "R": "🔥",
    "G": "🌿",
}

COLOR_HEX = {
    "W": "#f9f6e8",
    "U": "#4a90d9",
    "B": "#9b9b9b",
    "R": "#e05a3a",
    "G": "#4caf75",
}


@dataclass
class Commander:
    """Représente un commandant MTG jouable."""

    id: int
    name: str
    colors: list[str] = field(default_factory=list)
    image_path: str | None = field(default=None)

    @property
    def color_identity(self) -> str:
        """Retourne l'identité de couleur triée selon l'ordre WUBRG."""
        return "".join(c for c in MTG_COLORS if c in self.colors)

    @property
    def is_colorless(self) -> bool:
        return len(self.colors) == 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "colors": self.colors,
            "image_path": self.image_path,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Commander":
        return cls(
            id=data["id"],
            name=data["name"],
            colors=data.get("colors", []),
            image_path=data.get("image_path"),
        )
