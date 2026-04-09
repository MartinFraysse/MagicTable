"""
Conteneur multi-tournois.

Affiche un onglet par tournoi actif. Chaque onglet contient un DashboardViewMain
indépendant avec son propre timer, historique undo, et état.

États :
  - Aucun tournoi  → écran vide "Lancez un tournoi…"
  - ≥ 1 tournoi   → QTabWidget avec les onglets actifs
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QStackedWidget, QTabWidget, QLabel,
)
from PySide6.QtCore import Signal, Qt

from core.tournament import Tournament
from ui.dashboard.dashboard_view_main import DashboardViewMain


class MultiDashboardContainer(QWidget):
    """
    Relaie les signaux de chaque DashboardViewMain vers MainWindow.
    Gère l'ouverture, la fermeture et le focus des onglets.
    """

    tournament_changed  = Signal()
    tournament_archived = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)

        # _dashboards : tournament_id → DashboardViewMain
        self._dashboards: dict[int, DashboardViewMain] = {}

        self._build_ui()

    # ──────────────────────────────────────────────────────────
    # UI
    # ──────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget()
        self._stack.setAttribute(Qt.WA_StyledBackground, True)
        layout.addWidget(self._stack)

        # Index 0 — état vide
        self._empty_label = QLabel(
            "Aucun tournoi en cours\n\n"
            "Allez dans  🏆 Tournois  pour en lancer un."
        )
        self._empty_label.setObjectName("DashboardEmptyLabel")
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._stack.addWidget(self._empty_label)

        # Index 1 — onglets
        self._tabs = QTabWidget()
        self._tabs.setObjectName("DashboardTabs")
        self._tabs.setTabsClosable(True)
        self._tabs.tabCloseRequested.connect(self._on_tab_close_requested)
        self._stack.addWidget(self._tabs)

        self._stack.setCurrentIndex(0)

    # ──────────────────────────────────────────────────────────
    # API publique
    # ──────────────────────────────────────────────────────────

    def start_tournament(self, tournament: Tournament, timer_minutes: int | None = None) -> None:
        """
        Ouvre un onglet pour ce tournoi, ou bascule dessus s'il est déjà ouvert.
        """
        if tournament.id in self._dashboards:
            self._focus_tab(tournament.id)
            return

        dashboard = DashboardViewMain()
        dashboard.tournament_changed.connect(self.tournament_changed)
        dashboard.tournament_archived.connect(self._on_dashboard_archived)
        dashboard.tournament_quit.connect(self._remove_dashboard)

        self._dashboards[tournament.id] = dashboard

        label = self._tab_label(tournament)
        idx = self._tabs.addTab(dashboard, label)
        self._tabs.setCurrentIndex(idx)
        self._stack.setCurrentIndex(1)

        dashboard.set_current_round(tournament, timer_minutes)

    def close_all(self) -> None:
        """Ferme tous les onglets sans confirmation (ex. : suppression globale)."""
        for dashboard in list(self._dashboards.values()):
            dashboard._clear_dashboard()
        self._dashboards.clear()
        while self._tabs.count():
            self._tabs.removeTab(0)
        self._stack.setCurrentIndex(0)

    # ──────────────────────────────────────────────────────────
    # Slots internes
    # ──────────────────────────────────────────────────────────

    def _on_tab_close_requested(self, index: int) -> None:
        """Clic sur le × d'un onglet → délègue au dashboard (confirmation incluse)."""
        widget = self._tabs.widget(index)
        if isinstance(widget, DashboardViewMain):
            widget._quit_tournament()

    def _on_dashboard_archived(self, tournament_id: int) -> None:
        """Un tournoi vient d'être archivé → relayer + fermer l'onglet."""
        self.tournament_archived.emit(tournament_id)
        self._remove_dashboard(tournament_id)

    def _remove_dashboard(self, tournament_id: int) -> None:
        """Retire l'onglet correspondant à ce tournoi."""
        dashboard = self._dashboards.pop(tournament_id, None)
        if dashboard is None:
            return

        for i in range(self._tabs.count()):
            if self._tabs.widget(i) is dashboard:
                self._tabs.removeTab(i)
                break

        if self._tabs.count() == 0:
            self._stack.setCurrentIndex(0)

    # ──────────────────────────────────────────────────────────
    # Helpers
    # ──────────────────────────────────────────────────────────

    def _focus_tab(self, tournament_id: int) -> None:
        dashboard = self._dashboards.get(tournament_id)
        if dashboard is None:
            return
        for i in range(self._tabs.count()):
            if self._tabs.widget(i) is dashboard:
                self._tabs.setCurrentIndex(i)
                self._stack.setCurrentIndex(1)
                return

    @staticmethod
    def _tab_label(tournament: Tournament) -> str:
        """Génère le label de l'onglet : icône format + nom court."""
        icon = "👑" if tournament.format == "👑 Commander" else "⚔️"
        name = tournament.name if len(tournament.name) <= 20 else tournament.name[:18] + "…"
        return f"{icon} {name}"
