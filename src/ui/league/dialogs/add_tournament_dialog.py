"""Dialog pour ajouter un tournoi archivé à une ligue."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QScrollArea, QWidget,
    QFrame, QHBoxLayout, QDialogButtonBox, QPushButton,
)
from PySide6.QtCore import Qt

from core.league import League
from core.tournament import Tournament


class AddTournamentDialog(QDialog):
    """
    Affiche les tournois archivés compatibles (même format, pas déjà dans la ligue).
    """

    def __init__(self, parent, league: League, tournaments: list[Tournament]):
        super().__init__(parent)
        self.setWindowTitle("Ajouter un tournoi à la ligue")
        self.setMinimumWidth(440)
        self.setMinimumHeight(400)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("AddTournamentDialog")

        self._selected_id: int | None = None
        self._selected_card: QFrame | None = None

        already_in = set(league.tournament_ids)
        self._candidates = [
            t for t in tournaments
            if t.archived and t.format == league.format and t.id not in already_in
        ]

        self._build_ui(league)

    def _build_ui(self, league: League) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(14)
        root.setContentsMargins(20, 20, 20, 20)

        info = QLabel(
            f"Tournois archivés — format <b>{league.format}</b><br>"
            f"non encore inclus dans « {league.name} » :"
        )
        info.setWordWrap(True)
        info.setObjectName("AddTournamentInfo")
        root.addWidget(info)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("AddTournamentScroll")

        container = QWidget()
        container.setObjectName("AddTournamentContainer")
        self._cards_layout = QVBoxLayout(container)
        self._cards_layout.setContentsMargins(0, 0, 4, 0)
        self._cards_layout.setSpacing(8)

        if self._candidates:
            for t in self._candidates:
                card = self._make_card(t)
                self._cards_layout.addWidget(card)
        else:
            empty = QLabel("Aucun tournoi disponible pour ce format.")
            empty.setObjectName("AddTournamentEmpty")
            empty.setAlignment(Qt.AlignCenter)
            self._cards_layout.addWidget(empty)

        self._cards_layout.addStretch()
        scroll.setWidget(container)
        root.addWidget(scroll, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self._ok_btn = buttons.button(QDialogButtonBox.Ok)
        self._ok_btn.setEnabled(False)
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _make_card(self, t: Tournament) -> QFrame:
        card = QFrame()
        card.setObjectName("AddTournamentCard")
        card.setCursor(Qt.PointingHandCursor)
        card.setMinimumHeight(62)

        layout = QHBoxLayout(card)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        accent = QFrame()
        accent.setObjectName("AddTournamentCardAccent")
        accent.setFixedWidth(4)
        layout.addWidget(accent)

        col = QVBoxLayout()
        col.setSpacing(3)

        name_lbl = QLabel(t.name)
        name_lbl.setObjectName("AddTournamentCardName")

        meta_lbl = QLabel(f"{t.date}  •  {len(t.players)} joueurs")
        meta_lbl.setObjectName("AddTournamentCardMeta")

        col.addWidget(name_lbl)
        col.addWidget(meta_lbl)
        layout.addLayout(col)
        layout.addStretch()

        card.mousePressEvent = lambda _e, _t=t, _c=card: self._select(t.id, _c)
        card.mouseDoubleClickEvent = lambda _e, _t=t, _c=card: self._select_and_accept(t.id, _c)

        return card

    def _select(self, tid: int, card: QFrame) -> None:
        if self._selected_card:
            self._selected_card.setProperty("selected", False)
            self._selected_card.style().unpolish(self._selected_card)
            self._selected_card.style().polish(self._selected_card)

        self._selected_id = tid
        self._selected_card = card
        card.setProperty("selected", True)
        card.style().unpolish(card)
        card.style().polish(card)
        self._ok_btn.setEnabled(True)

    def _select_and_accept(self, tid: int, card: QFrame) -> None:
        self._select(tid, card)
        self.accept()

    def _on_accept(self) -> None:
        if self._selected_id is not None:
            self.accept()

    def selected_tournament_id(self) -> int | None:
        return self._selected_id
