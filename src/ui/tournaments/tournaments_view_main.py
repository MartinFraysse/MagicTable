from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
)
from PySide6.QtCore import Qt, Signal

from core.tournament import Tournament
from ui.tournaments.upcoming_view import UpcomingView
from ui.tournaments.launch_view import LaunchView
from ui.tournaments.historic_view import HistoricView
from ui.tournaments.dialogs.create_tournament import CreateTournamentDialog


class TournamentViewMain(QWidget):
    """
    Vue principale de la page Tournament.
    Orchestration entre Upcoming / Launch / Historic.
    """
    round_started = Signal(Tournament)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("TournamentViewMain")

        self._build_ui()
        self._connect_views()
        self._init_historic()

    # ======================================================
    # UI
    # ======================================================
    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(20)

        # =========================
        # Top area (Upcoming | Launch)
        # =========================
        top_container = QFrame()
        top_container.setObjectName("TournamentTopContainer")
        top_container.setAttribute(Qt.WA_StyledBackground, True)

        top_layout = QHBoxLayout(top_container)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(20)

        self.upcoming_container = self._build_upcoming_container()
        top_layout.addWidget(self.upcoming_container, 1)

        self.launch_container = self._build_launch_container()
        top_layout.addWidget(self.launch_container, 2)

        root_layout.addWidget(top_container, 1)

        # =========================
        # Bottom area (Historic)
        # =========================
        self.historic_container = self._build_historic_container()
        root_layout.addWidget(self.historic_container, 0)

    # ======================================================
    # Sub-containers
    # ======================================================
    def _build_upcoming_container(self):
        frame = QFrame()
        frame.setObjectName("UpcomingContainer")
        frame.setAttribute(Qt.WA_StyledBackground, True)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        self.upcoming_view = UpcomingView(self)
        layout.addWidget(self.upcoming_view)

        return frame

    def _build_launch_container(self):
        frame = QFrame()
        frame.setObjectName("LaunchContainer")
        frame.setAttribute(Qt.WA_StyledBackground, True)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        self.launch_view = LaunchView(self)
        layout.addWidget(self.launch_view)

        return frame

    def _build_historic_container(self):
        frame = QFrame()
        frame.setObjectName("HistoricContainer")
        frame.setAttribute(Qt.WA_StyledBackground, True)
        frame.setMinimumHeight(72)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        self.historic_view = HistoricView(self)
        layout.addWidget(self.historic_view)

        return frame

    # ======================================================
    # Connections (POINT CLÉ)
    # ======================================================
    def _connect_views(self):
        # Launch → Upcoming
        self.launch_view.tournament_taken.connect(
            self.upcoming_view.hide_tournament_card
        )

        self.launch_view.tournament_cancelled.connect(
            self.upcoming_view.show_tournament_card
        )

        # Upcoming → Launch
        self.upcoming_view.launch_requested.connect(
            self._launch_from_card
        )

        # Launch → Edit
        self.launch_view.edit_requested.connect(
            self._edit_from_launch
        )

        # Start Tournament
        self.launch_view.start_requested.connect(
            self._start_tournament
        )

    # ======================================================
    # Actions
    # ======================================================
    def _launch_from_card(self, tournament: Tournament):
        """
        Lance un tournoi dans LaunchView (clic droit).
        """
        if self.launch_view._current_tournament:
            return

        self.launch_view._load_tournament(tournament)
        self.upcoming_view.hide_tournament_card(tournament.id)

    def _edit_from_launch(self, tournament: Tournament):
        dialog = CreateTournamentDialog(self, tournament=tournament)

        if not dialog.exec():
            return

        old_league_id = dialog.get_old_league_id()
        new_league_id = dialog.get_selected_league_id()

        dialog.apply_changes()

        self.upcoming_view.refresh_tournament(tournament)
        self.launch_view._load_tournament(tournament)
        self.upcoming_view._update_league_affiliation(tournament.id, old_league_id, new_league_id)

    def _start_tournament(self, tournament: Tournament):
        # Ne créer un round que si le tournoi n'en a pas encore
        if not tournament.rounds:
            # Utiliser l'algorithme approprié selon le système d'appariement
            if tournament.is_swiss_format():
                tournament.create_round_swiss()
            else:
                tournament.create_round()

        self.round_started.emit(tournament)

        # Notifier le bot Discord à chaque lancement (création canaux si besoin)
        try:
            from sync.server_client import notify_start_async
            notify_start_async(tournament.id)
        except Exception as e:
            print(f"[sync] notify_start_async ignoré : {e}")

    def save_tournaments(self):
        """Sauvegarde tous les tournois (appelé depuis le dashboard)."""
        self.upcoming_view._save_all()

    def _init_historic(self):
        """Initialise la vue historique avec les tournois archivés."""
        self.historic_view.refresh_archived_tournaments(self.upcoming_view._tournaments)
        self.historic_view.tournament_deleted.connect(self._on_historic_tournament_deleted)
        self.historic_view.tournaments_changed.connect(self._on_historic_tournaments_changed)

    def _on_historic_tournaments_changed(self):
        """Appelé quand les données d'un tournoi archivé sont modifiées."""
        self.upcoming_view._save_all()

    def _on_historic_tournament_deleted(self, tournament_id: int):
        """Appelé quand un tournoi archivé est supprimé depuis l'historique."""
        self.upcoming_view._tournaments = [
            t for t in self.upcoming_view._tournaments if t.id != tournament_id
        ]
        self.upcoming_view._save_all()

    def on_tournament_archived(self, tournament_id: int):
        """Appelé quand un tournoi est archivé depuis le dashboard."""
        self.upcoming_view.remove_archived_tournament(tournament_id)
        self.launch_view._clear_tournament()
        self.historic_view.refresh_archived_tournaments(self.upcoming_view._tournaments)
 