"""Historique des états d'un tournoi pour le système d'annulation (undo)."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.tournament import Tournament


class TournamentHistory:
    """
    Pile de snapshots sérialisés d'un tournoi.

    Chaque snapshot est un dict produit par tournament.to_dict().
    L'annulation restaure le dernier snapshot sauvegardé.

    Utilisation :
        history.snapshot(tournament)   # avant toute mutation
        if history.can_undo():
            history.undo(tournament)   # restaure le dernier état
    """

    MAX_SNAPSHOTS = 20

    def __init__(self) -> None:
        self._stack: list[dict] = []

    def snapshot(self, tournament: Tournament) -> None:
        """Sauvegarde l'état actuel du tournoi avant une mutation."""
        self._stack.append(tournament.to_dict())
        if len(self._stack) > self.MAX_SNAPSHOTS:
            self._stack.pop(0)

    def can_undo(self) -> bool:
        return bool(self._stack)

    def undo(self, tournament: Tournament) -> None:
        """
        Restaure le dernier snapshot dans le tournoi passé en paramètre.
        Le tournoi est modifié en place (la référence reste la même).
        """
        data = self._stack.pop()
        tournament.restore_from_dict(data)

    def clear(self) -> None:
        self._stack.clear()
