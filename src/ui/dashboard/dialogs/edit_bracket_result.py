from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QFrame, QLayout
)
from PySide6.QtCore import Qt

from core.bracket import BracketMatch, BracketRoundName
from core.player import Player

_ROUND_LABELS = {
    BracketRoundName.QUART: "Quart de finale",
    BracketRoundName.DEMI:  "Demi-finale",
    BracketRoundName.FINAL: "Finale",
}


class EditBracketResultDialog(QDialog):
    """Dialog compact pour saisir le vainqueur d'un match de bracket."""

    def __init__(self, parent, match: BracketMatch, players_by_id: dict[int, Player]):
        super().__init__(parent)
        self.setWindowTitle("Résultat")
        self.setModal(True)
        self.setObjectName("EditBracketResultDialog")
        self.setFixedWidth(260)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._winner_id: int | None = None

        p1 = players_by_id.get(match.player1_id)
        p2 = players_by_id.get(match.player2_id)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSizeConstraint(QLayout.SetFixedSize)

        # ── Sous-titre round ─────────────────────────────────────────
        round_lbl = QLabel(_ROUND_LABELS.get(match.round_name, "Match"))
        round_lbl.setObjectName("BracketRoundSubtitle")
        round_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(round_lbl)

        # ── Titre ────────────────────────────────────────────────────
        title = QLabel("Vainqueur ?")
        title.setObjectName("BracketResultTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        layout.addSpacing(4)

        # ── Bouton joueur 1 ──────────────────────────────────────────
        if p1:
            btn1 = QPushButton(p1.name)
            btn1.setObjectName("BracketWinnerButton")
            btn1.setFixedHeight(42)
            btn1.setCursor(Qt.PointingHandCursor)
            btn1.clicked.connect(lambda: self._select(p1.id))
            layout.addWidget(btn1)

        # ── Séparateur VS ────────────────────────────────────────────
        vs_row = QHBoxLayout()
        line_l = QFrame()
        line_l.setFrameShape(QFrame.HLine)
        line_l.setObjectName("BracketVsSeparator")
        vs_lbl = QLabel("VS")
        vs_lbl.setObjectName("BracketVsLabel")
        vs_lbl.setAlignment(Qt.AlignCenter)
        vs_lbl.setFixedWidth(32)
        line_r = QFrame()
        line_r.setFrameShape(QFrame.HLine)
        line_r.setObjectName("BracketVsSeparator")
        vs_row.addWidget(line_l)
        vs_row.addWidget(vs_lbl)
        vs_row.addWidget(line_r)
        layout.addLayout(vs_row)

        # ── Bouton joueur 2 ──────────────────────────────────────────
        if p2:
            btn2 = QPushButton(p2.name)
            btn2.setObjectName("BracketWinnerButton")
            btn2.setFixedHeight(42)
            btn2.setCursor(Qt.PointingHandCursor)
            btn2.clicked.connect(lambda: self._select(p2.id))
            layout.addWidget(btn2)

        layout.addSpacing(4)

        # ── Annuler ──────────────────────────────────────────────────
        cancel_btn = QPushButton("Annuler")
        cancel_btn.setObjectName("BracketCancelButton")
        cancel_btn.setFixedHeight(28)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn, alignment=Qt.AlignCenter)

    def _select(self, player_id: int):
        self._winner_id = player_id
        self.accept()

    def winner_id(self) -> int | None:
        return self._winner_id
