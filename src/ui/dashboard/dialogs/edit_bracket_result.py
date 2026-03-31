from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
)
from PySide6.QtCore import Qt

from core.bracket import BracketMatch
from core.player import Player


class EditBracketResultDialog(QDialog):
    """Dialog pour saisir le résultat d'un match de bracket — qui a gagné?"""

    def __init__(self, parent, match: BracketMatch, players_by_id: dict[int, Player]):
        super().__init__(parent)
        self.setWindowTitle("Résultat du match")
        self.setModal(True)
        self.setObjectName("EditBracketResultDialog")
        self.setMinimumWidth(340)

        self._winner_id: int | None = None

        p1 = players_by_id.get(match.player1_id)
        p2 = players_by_id.get(match.player2_id)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Qui a gagné ?")
        title.setObjectName("DialogTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        if p1:
            vs_label = QLabel(f"{p1.name}  vs  {p2.name if p2 else '?'}")
        else:
            vs_label = QLabel("Match en attente")
        vs_label.setObjectName("BracketMatchVsLabel")
        vs_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(vs_label)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        if p1:
            btn1 = QPushButton(p1.name)
            btn1.setObjectName("BracketWinnerButton")
            btn1.setMinimumHeight(48)
            btn1.clicked.connect(lambda: self._select(p1.id))
            btn_row.addWidget(btn1)

        if p2:
            btn2 = QPushButton(p2.name)
            btn2.setObjectName("BracketWinnerButton")
            btn2.setMinimumHeight(48)
            btn2.clicked.connect(lambda: self._select(p2.id))
            btn_row.addWidget(btn2)

        layout.addLayout(btn_row)

        cancel_btn = QPushButton("Annuler")
        cancel_btn.setObjectName("SecondaryButton")
        cancel_btn.setMinimumHeight(36)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

    def _select(self, player_id: int):
        self._winner_id = player_id
        self.accept()

    def winner_id(self) -> int | None:
        return self._winner_id
