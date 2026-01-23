from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QFrame,
    QLabel,
    QDialog,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)

from core.tournament import Tournament


class HistoricView(QWidget):
    """
    Vue d'accès à l'historique des tournois archivés.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("HistoricView")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._archived_tournaments: list[Tournament] = []

        self._build_ui()

    # =========================
    # UI
    # =========================
    def _build_ui(self):
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        container = QFrame()
        container.setObjectName("HistoricContainerInner")
        container.setAttribute(Qt.WA_StyledBackground, True)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(12, 8, 12, 8)

        layout.addStretch()

        self.history_btn = QPushButton("📜 Historique des tournois")
        self.history_btn.setObjectName("HistoricPrimaryButton")
        self.history_btn.setCursor(Qt.PointingHandCursor)
        self.history_btn.clicked.connect(self._show_history_dialog)

        self.count_label = QLabel("")
        self.count_label.setObjectName("HistoricCountLabel")

        layout.addWidget(self.history_btn)
        layout.addWidget(self.count_label)

        root_layout.addWidget(container, 1)

    # =========================
    # Public API
    # =========================
    def refresh_archived_tournaments(self, all_tournaments: list[Tournament]):
        """Met à jour la liste des tournois archivés."""
        self._archived_tournaments = [t for t in all_tournaments if t.archived]
        count = len(self._archived_tournaments)
        if count > 0:
            self.count_label.setText(f"({count})")
        else:
            self.count_label.setText("")

    # =========================
    # Dialog
    # =========================
    def _show_history_dialog(self):
        if not self._archived_tournaments:
            return

        dialog = HistoricDialog(self, self._archived_tournaments)
        dialog.exec()


class HistoricDialog(QDialog):
    """Dialog affichant la liste des tournois archivés."""

    def __init__(self, parent, tournaments: list[Tournament]):
        super().__init__(parent)

        self.setWindowTitle("Historique des tournois")
        self.setModal(True)
        self.setMinimumSize(600, 500)
        self.setObjectName("HistoricDialog")

        self._tournaments = tournaments

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("📜 Tournois archivés")
        title.setObjectName("DialogTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Liste des tournois
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(12)

        for tournament in self._tournaments:
            card = self._create_tournament_card(tournament)
            content_layout.addWidget(card)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Bouton fermer
        close_btn = QPushButton("Fermer")
        close_btn.setObjectName("CancelButton")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)

    def _create_tournament_card(self, tournament: Tournament) -> QFrame:
        card = QFrame()
        card.setObjectName("HistoricCard")

        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        # Header
        header = QHBoxLayout()
        name_label = QLabel(f"<b>{tournament.name}</b>")
        name_label.setObjectName("HistoricCardTitle")

        format_label = QLabel(tournament.format)
        format_label.setObjectName("HistoricCardFormat")

        date_label = QLabel(tournament.date)
        date_label.setObjectName("HistoricCardDate")

        header.addWidget(name_label)
        header.addWidget(format_label)
        header.addStretch()
        header.addWidget(date_label)

        layout.addLayout(header)

        # Classement (top 3)
        players = sorted(tournament.players, key=lambda p: (-p.score, p.name))

        ranking_layout = QHBoxLayout()
        for rank, player in enumerate(players[:3], 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, "")
            label = QLabel(f"{medal} {player.name} ({player.score} pts)")
            label.setObjectName("HistoricCardRanking")
            ranking_layout.addWidget(label)

        ranking_layout.addStretch()
        layout.addLayout(ranking_layout)

        # Stats
        stats = QLabel(f"{len(tournament.players)} joueurs • {len(tournament.rounds)} rounds")
        stats.setObjectName("HistoricCardStats")
        layout.addWidget(stats)

        return card
