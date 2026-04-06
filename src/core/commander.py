from dataclasses import dataclass, field


_COLOR_EMOJI = {"W": "☀️", "U": "💧", "B": "💀", "R": "🔥", "G": "🌿"}

_FORMAT_LABELS = {
    "both":       "Les deux",
    "commander":  "👑 Commander Multi",
    "duel":       "⚔️ Duel Commander",
}


@dataclass
class Commander:
    """Commandant enregistré dans la base de données."""

    id: int
    name: str
    colors: str = ""    # sous-ensemble de "WUBRG", ex: "WUB"
    format: str = "both"  # "both", "commander", "duel"

    @property
    def format_label(self) -> str:
        return _FORMAT_LABELS.get(self.format, self.format)

    @property
    def colors_display(self) -> str:
        if not self.colors:
            return "—"
        return " ".join(_COLOR_EMOJI.get(c.upper(), c) for c in self.colors.upper() if c in _COLOR_EMOJI)

    def to_dict(self) -> dict:
        return {
            "id":     self.id,
            "name":   self.name,
            "colors": self.colors,
            "format": self.format,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Commander":
        return cls(
            id=data["id"],
            name=data["name"],
            colors=data.get("colors", ""),
            format=data.get("format", "both"),
        )
