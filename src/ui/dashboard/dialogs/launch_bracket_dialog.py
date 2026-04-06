from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QPushButton, QLabel, QFrame, QLayout, QHBoxLayout
)
from PySide6.QtCore import Qt

from core.bracket import BracketType

_OPTIONS = [
    (
        BracketType.FINAL,
        "🥇",
        "Top 2",
        "Finale directe",
        2,
    ),
    (
        BracketType.DEMI_FINALE,
        "🥈",
        "Top 4",
        "Demi-finales  +  Finale",
        4,
    ),
    (
        BracketType.QUART_DE_FINALE,
        "🥉",
        "Top 8",
        "Quarts  +  Demis  +  Finale",
        8,
    ),
]


class LaunchBracketDialog(QDialog):
    """Dialog compact pour choisir le format du bracket d'élimination."""

    def __init__(self, parent, player_count: int):
        super().__init__(parent)
        self.setWindowTitle("Phase finale")
        self.setModal(True)
        self.setObjectName("LaunchBracketDialog")
        self.setFixedWidth(270)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._bracket_type: BracketType | None = None

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSizeConstraint(QLayout.SetFixedSize)

        # ── Titre ────────────────────────────────────────────────────
        title = QLabel("🏆  Phase finale")
        title.setObjectName("BracketResultTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Choisir le format")
        subtitle.setObjectName("BracketRoundSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        layout.addSpacing(4)

        # ── Cartes d'option ──────────────────────────────────────────
        available = [opt for opt in _OPTIONS if player_count >= opt[4]]

        for bracket_type, icon, top_label, desc_label, _ in reversed(available):
            card = self._option_card(bracket_type, icon, top_label, desc_label)
            layout.addWidget(card)

        layout.addSpacing(4)

        # ── Annuler ──────────────────────────────────────────────────
        cancel_btn = QPushButton("Annuler")
        cancel_btn.setObjectName("BracketCancelButton")
        cancel_btn.setFixedHeight(28)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn, alignment=Qt.AlignCenter)

    # ------------------------------------------------------------------
    def _option_card(
        self,
        bracket_type: BracketType,
        icon: str,
        top_label: str,
        desc_label: str,
    ) -> QFrame:
        card = QFrame()
        card.setObjectName("BracketOptionCard")
        card.setCursor(Qt.PointingHandCursor)
        card.setAttribute(Qt.WA_StyledBackground, True)

        row = QHBoxLayout(card)
        row.setContentsMargins(12, 10, 12, 10)
        row.setSpacing(10)

        icon_lbl = QLabel(icon)
        icon_lbl.setObjectName("BracketOptionIcon")
        icon_lbl.setFixedWidth(24)
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)

        text_col = QVBoxLayout()
        text_col.setSpacing(1)

        top = QLabel(top_label)
        top.setObjectName("BracketOptionTitle")
        top.setAttribute(Qt.WA_TransparentForMouseEvents)

        desc = QLabel(desc_label)
        desc.setObjectName("BracketOptionDesc")
        desc.setAttribute(Qt.WA_TransparentForMouseEvents)

        text_col.addWidget(top)
        text_col.addWidget(desc)

        row.addWidget(icon_lbl)
        row.addLayout(text_col)
        row.addStretch()

        # Clic sur la carte
        card.mousePressEvent = lambda e, bt=bracket_type: self._select(bt)

        return card

    def _select(self, bracket_type: BracketType):
        self._bracket_type = bracket_type
        self.accept()

    def bracket_type(self) -> BracketType | None:
        return self._bracket_type
