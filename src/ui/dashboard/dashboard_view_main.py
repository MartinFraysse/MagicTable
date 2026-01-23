from PySide6.QtWidgets import QWidget, QVBoxLayout, QSpacerItem
from PySide6.QtCore import QTimer

from ui.dashboard.tiles_view import DashboardTilesView
from ui.dashboard.ranking_view import DashboardRankingView
from ui.dashboard.tables_view import DashboardTablesView
from ui.dashboard.round_controls_view import DashboardRoundControlsView
from ui.dashboard.dialogs.edit_table_results import EditTableResultsDialog

from core.tournament import Tournament
from core.table import Table
from core.round import Round


class DashboardViewMain(QWidget):
    WINDOW_HEIGHT = 880
    RANKING_RATIO = 0.61   # priorité légère au classement
    GAP_BETWEEN_CARDS = 24  # 👈 ESPACE VISUEL ENTRE RANKING ET TABLES

    def __init__(self, parent=None):
        super().__init__(parent)

        self.current_tournament: Tournament | None = None
        self.current_round: Round | None = None

        # =====================
        # Layout
        # =====================
        root = QVBoxLayout(self)
        root.setSpacing(30)
        root.setContentsMargins(0, 0, 0, 0)

        # === TUILES (hauteur naturelle)
        self.tiles_view = DashboardTilesView(self)
        root.addWidget(self.tiles_view, 0)

        # === CLASSEMENT
        self.ranking_view = DashboardRankingView(self)
        root.addWidget(self.ranking_view, 0)

        # 🔑 ESPACE VISUEL ENTRE LES DEUX FRAMES
        root.addSpacerItem(
            QSpacerItem(0, self.GAP_BETWEEN_CARDS)
        )

        # === TABLES
        self.tables_view = DashboardTablesView(self)
        root.addWidget(self.tables_view, 0)
        self.tables_view.edit_results_requested.connect(
            self._edit_table_results
        )

        # === CONTROLES
        self.round_controls = DashboardRoundControlsView(self)
        root.addWidget(self.round_controls, 0)

        self.round_controls.set_start_enabled(False)
        self.round_controls.set_next_enabled(False)

        self.round_controls.start_round_requested.connect(self._start_round)
        self.round_controls.next_round_requested.connect(self._next_round)

        # =====================
        # Timer
        # =====================
        self.remaining_seconds = 50 * 60
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

        # =====================
        # Calcul initial des hauteurs
        # =====================
        self._recompute_layout_heights()

    # ======================================================
    # Layout sizing logic
    # ======================================================
    def _recompute_layout_heights(self):
        # 3 spacings du layout + 1 spacer manuel
        spacing = (30 * 3) + self.GAP_BETWEEN_CARDS

        tiles_h = self.tiles_view.sizeHint().height()
        controls_h = self.round_controls.sizeHint().height()

        available = (
            self.WINDOW_HEIGHT
            - tiles_h
            - controls_h
            - spacing
        )

        ranking_h = int(available * self.RANKING_RATIO)
        tables_h = available - ranking_h

        self.ranking_view.setFixedHeight(ranking_h)
        self.tables_view.setFixedHeight(tables_h)

    # ======================================================
    # Timer
    # ======================================================
    def _tick(self):
        if self.remaining_seconds <= 0:
            self.timer.stop()
            return

        self.remaining_seconds -= 1
        m = self.remaining_seconds // 60
        s = self.remaining_seconds % 60
        self.tiles_view.set_timer_text(f"{m:02d}:{s:02d}")

    def _reset_timer(self, minutes: int = 50):
        self.remaining_seconds = minutes * 60
        self.tiles_view.set_timer_text(f"{minutes:02d}:00")

    # ======================================================
    # Round lifecycle
    # ======================================================
    def set_current_round(self, tournament: Tournament):
        if not tournament.rounds:
            return

        self.current_tournament = tournament
        self.current_round = tournament.rounds[-1]

        self.timer.stop()
        self._reset_timer()

        self.round_controls.set_start_enabled(True)
        self.round_controls.set_next_enabled(False)

        self.ranking_view.set_tournament(tournament)

        self.tiles_view.update_for_tournament(
            name=tournament.name,
            round_number=self.current_round.number,
            player_count=len(tournament.players),
            table_count=len(self.current_round.tables),
        )

        self.tables_view.set_round(self.current_round)

        # recalcul au cas où
        self._recompute_layout_heights()

    def _start_round(self):
        if not self.current_round:
            return

        self.timer.start(1000)
        self.round_controls.set_start_enabled(False)

    def _all_tables_finished(self) -> bool:
        return (
            self.current_round is not None
            and all(table.finished for table in self.current_round.tables)
        )

    def _next_round(self):
        if not self.current_tournament or not self._all_tables_finished():
            return

        self.current_tournament.create_round()
        self.set_current_round(self.current_tournament)

    # ======================================================
    # Table results
    # ======================================================
    def _edit_table_results(self, table: Table):
        dialog = EditTableResultsDialog(self, table)

        if not dialog.exec():
            return

        table.results = dialog.results()
        table.finished = True

        self.tables_view.set_round(self.current_round)

        if self._all_tables_finished():
            self.round_controls.set_next_enabled(True)
