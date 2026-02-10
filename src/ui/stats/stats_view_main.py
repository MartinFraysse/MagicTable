"""Vue principale des statistiques."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QTabWidget, QFrame
from PySide6.QtCore import Qt

from core.tournament import Tournament
from core.stats_analyzer import StatsAnalyzer
from core.regular_player import RegularPlayer
from storage.tournaments import TournamentStorage
from storage.regular_players import RegularPlayerStorage

from ui.stats.global_stats_view import GlobalStatsView
from ui.stats.rankings_view import RankingsView
from ui.stats.head_to_head_view import HeadToHeadView


class StatsViewMain(QWidget):
    """Vue principale des statistiques avec onglets."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("StatsViewMain")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setObjectName("StatsTabs")
        self.tabs.tabBar().setObjectName("StatsTabBar")
        self.tabs.tabBar().setDrawBase(False)

        # Onglets
        self.global_stats_view = GlobalStatsView()
        self.rankings_view = RankingsView()
        self.head_to_head_view = HeadToHeadView()

        self.tabs.addTab(self.global_stats_view, "   Stats Globales")
        self.tabs.addTab(self.rankings_view, "   Classement")
        self.tabs.addTab(self.head_to_head_view, "   Head-to-Head")

        layout.addWidget(self.tabs)

    def refresh(self):
        """Recharge les statistiques depuis les tournois archivés."""
        # Charger les tournois
        raw_tournaments = TournamentStorage.load()
        tournaments = [Tournament.from_dict(t) for t in raw_tournaments]

        # Charger les joueurs réguliers
        raw_regular = RegularPlayerStorage.load()
        regular_players = [RegularPlayer.from_dict(d) for d in raw_regular]
        regular_pseudos = {p.pseudo.lower().strip() for p in regular_players}

        # Créer l'analyseur (filtre automatiquement les tournois archivés)
        analyzer = StatsAnalyzer(tournaments)

        # Mettre à jour les vues
        self.global_stats_view.update_stats(analyzer)
        self.rankings_view.update_stats(analyzer, regular_pseudos)
        self.head_to_head_view.update_stats(analyzer, regular_pseudos)
