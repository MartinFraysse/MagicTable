"""
Formats de tournoi supportés.

Les libellés (emoji compris) sont stockés tels quels dans les tournois et les
ligues sauvegardés : ne pas les modifier sans migrer les données.
"""

FORMAT_COMMANDER = "👑 Commander"
FORMAT_DUEL_COMMANDER = "⚔️ Duel Commander"

FORMATS: list[str] = [
    FORMAT_COMMANDER,
    FORMAT_DUEL_COMMANDER,
    "🃏 Draft",
    "🏆 AP",
    "⚡ Pokemon",
    "🔥 Rise",
]


def is_multiplayer_format(fmt: str) -> bool:
    """True pour le Commander multijoueur (tables de 3-4), False pour les formats 1v1."""
    return fmt == FORMAT_COMMANDER
