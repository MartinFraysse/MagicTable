from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QColor


class FinalStandingsOverlay(QWidget):
    """
    Tuile superposée sur le dashboard affichant le classement final.
    S'affiche directement dans le widget parent sans ouvrir de fenêtre.
    """
    dismissed = Signal()

    ROW_H = 32       # hauteur par ligne (font 13px + padding vertical)
    MAX_VISIBLE = 8  # max lignes avant scroll

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.hide()

    # ------------------------------------------------------------------
    # Construction de l'UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)

        # ── Carte centrale ────────────────────────────────────────────
        self.card = QFrame()
        self.card.setObjectName("FinalCard")
        self.card.setAttribute(Qt.WA_StyledBackground, True)
        self.card.setFixedWidth(320)
        # Empêche l'étirement vertical : la carte prend sa taille naturelle
        self.card.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Maximum)

        card_layout = QVBoxLayout(self.card)
        card_layout.setSpacing(0)
        card_layout.setContentsMargins(20, 18, 20, 18)

        # Titre tournoi
        self.title_lbl = QLabel()
        self.title_lbl.setObjectName("FinalTitle")
        self.title_lbl.setAlignment(Qt.AlignCenter)
        self.title_lbl.setWordWrap(True)
        card_layout.addWidget(self.title_lbl)

        card_layout.addSpacing(4)

        # Sous-titre
        subtitle = QLabel("CLASSEMENT FINAL")
        subtitle.setObjectName("FinalSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(subtitle)

        card_layout.addSpacing(10)

        # Zone scrollable — fond transparent, hauteur dynamique
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setObjectName("FinalScroll")
        # Transparent pour ne pas masquer le fond de la carte
        self.scroll.setAutoFillBackground(False)
        self.scroll.viewport().setAutoFillBackground(False)

        self.content_widget = QWidget()
        self.content_widget.setAttribute(Qt.WA_StyledBackground, True)
        self.content_widget.setObjectName("FinalContent")
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(3)
        self.content_layout.setContentsMargins(0, 0, 4, 0)
        self.scroll.setWidget(self.content_widget)
        card_layout.addWidget(self.scroll)

        card_layout.addSpacing(14)

        # Bouton fermer centré
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Fermer")
        close_btn.setObjectName("PrimaryButton")
        close_btn.setMinimumHeight(36)
        close_btn.setMinimumWidth(100)
        close_btn.clicked.connect(self._dismiss)
        btn_row.addWidget(close_btn)
        btn_row.addStretch()
        card_layout.addLayout(btn_row)

        layout.addWidget(self.card)

    # ------------------------------------------------------------------
    # API publique
    # ------------------------------------------------------------------
    def show_standings(self, tournament_name: str, players: list):
        """Affiche le classement final par-dessus le dashboard."""
        self.title_lbl.setText(f"🏆  {tournament_name}")

        # Vider les lignes précédentes
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        row_styles = {1: "FinalRowGold", 2: "FinalRowSilver", 3: "FinalRowBronze"}
        for rank, player in enumerate(players, 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank:>2}.")
            lbl = QLabel(f"{medal}  {player.name}  —  {player.score} pts")
            lbl.setObjectName(row_styles.get(rank, "FinalRow"))
            lbl.setAttribute(Qt.WA_StyledBackground, True)
            self.content_layout.addWidget(lbl)

        # Pousse les lignes vers le haut (évite l'étirement)
        self.content_layout.addStretch()

        # Hauteur proportionnelle, plafonnée à MAX_VISIBLE lignes
        self.scroll.setFixedHeight(min(len(players), self.MAX_VISIBLE) * self.ROW_H)

        self._fit_to_parent()
        self.show()
        self.raise_()

    def fit_to_parent(self):
        """Appelé par le parent lors d'un resize pour rester couvrant."""
        if self.isVisible():
            self._fit_to_parent()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _dismiss(self):
        self.hide()
        self.dismissed.emit()

    def _fit_to_parent(self):
        if self.parent():
            self.setGeometry(self.parent().rect())

    def paintEvent(self, event):
        """Fond semi-transparent par-dessus le dashboard."""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 160))
