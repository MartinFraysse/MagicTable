"""Vue Stats globales des commandants — intégrée dans l'onglet Stats."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget, QLabel, QScrollArea, QFrame,
)
from PySide6.QtCore import Qt

from ui.commanders.dialogs.commander_stats import (
    _compute_global_stats,
    _make_podium_row,
    _make_ranking_scroll,
)


class CommanderGlobalStatsView(QWidget):
    """
    Stats globales des commandants : Victoires / Multi / Duel.
    Trois onglets affichés directement dans la vue Stats principale.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CommanderGlobalStatsView")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._tabs = QTabWidget()
        self._tabs.setObjectName("StatsTabWidget")

        layout.addWidget(self._tabs)

    def refresh(self):
        """Recalcule et rafraîchit les données depuis le stockage."""
        data = _compute_global_stats()

        self._tabs.clear()
        self._tabs.addTab(
            self._build_tab(data["wins"],  "victoire(s)", "Aucune victoire enregistrée."),
            "🏆 Victoires",
        )

    def _build_tab(self, data: list, suffix: str, empty_msg: str) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        if not data:
            lbl = QLabel(empty_msg)
            lbl.setObjectName("StatsLabel")
            lbl.setAlignment(Qt.AlignCenter)
            lay.addWidget(lbl)
            lay.addStretch()
            return page

        # Podium (top 3)
        lay.addLayout(_make_podium_row(data, suffix))

        # Classement complet si plus de 3 entrées
        if len(data) > 3:
            sep = QLabel("Classement complet")
            sep.setObjectName("StatsSectionTitle")
            lay.addWidget(sep)
            lay.addWidget(_make_ranking_scroll(data, suffix), 1)

        return page
