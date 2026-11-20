from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QFrame, QLabel

from core.tournament import Tournament
from ui.tournaments.dialogs.historic_dialogs import HistoricDialog


class HistoricView(QWidget):
    """
    Vue d'accès à l'historique des tournois archivés.
    """

    tournament_deleted = Signal(int)  # Émet l'ID du tournoi supprimé
    tournaments_changed = Signal()  # Émet quand les données sont modifiées

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
        dialog.tournament_deleted.connect(self._on_tournament_deleted)
        dialog.tournaments_changed.connect(self._on_tournaments_changed)
        dialog.exec()

    def _on_tournaments_changed(self):
        """Appelé quand les données d'un tournoi sont modifiées."""
        self.tournaments_changed.emit()

    def _on_tournament_deleted(self, tournament_id: int):
        """Appelé quand un tournoi est supprimé depuis le dialog."""
        self._archived_tournaments = [
            t for t in self._archived_tournaments if t.id != tournament_id
        ]
        count = len(self._archived_tournaments)
        if count > 0:
            self.count_label.setText(f"({count})")
        else:
            self.count_label.setText("")
        self.tournament_deleted.emit(tournament_id)






