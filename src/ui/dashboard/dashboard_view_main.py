from PySide6.QtWidgets import QWidget, QVBoxLayout, QSpacerItem, QMessageBox
from PySide6.QtCore import QTimer, Signal

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

    # Signal émis quand le tournoi doit être sauvegardé
    tournament_changed = Signal()
    # Signal émis quand le tournoi est archivé (avec l'ID du tournoi)
    tournament_archived = Signal(int)

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
        self.round_controls.shuffle_round_requested.connect(self._shuffle_round)
        self.round_controls.reset_requested.connect(self._reset_tournament)
        self.round_controls.archive_requested.connect(self._archive_tournament)

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
            max_rounds=tournament.max_rounds,
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

        if not self.current_tournament.can_create_round():
            self._finish_tournament()
            return

        self.current_tournament.create_round()
        self.set_current_round(self.current_tournament)

        # Cacher l'alerte de répétition
        self.round_controls.hide_repetition_warning()

        # Notifier pour sauvegarder
        self.tournament_changed.emit()

    def _finish_tournament(self):
        """Affiche le classement final quand le tournoi est terminé."""
        players = sorted(
            self.current_tournament.players,
            key=lambda p: (-p.score, -p.robustness, p.name)
        )

        # Print dans le terminal
        print(f"\n{'='*60}")
        print(f"🏆 TOURNOI TERMINÉ - {self.current_tournament.name}")
        print(f"{'='*60}")
        print(f"\n📊 CLASSEMENT FINAL:\n")

        for rank, player in enumerate(players, 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, "  ")
            print(f"  {medal} {rank}. {player.name:<20} {player.score} pts")

        print(f"\n{'='*60}\n")

        # Désactiver le bouton suivant et afficher le bouton d'archivage
        self.round_controls.set_next_enabled(False)
        self.round_controls.show_archive_button()

        # Popup de fin de tournoi
        ranking_text = ""
        for rank, player in enumerate(players[:10], 1):  # Top 10
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"{rank}.")
            ranking_text += f"{medal} {player.name} — {player.score} pts\n"

        msg = QMessageBox(self)
        msg.setWindowTitle("Tournoi terminé")
        msg.setIcon(QMessageBox.Information)
        msg.setText(f"🏆 {self.current_tournament.name} est terminé !")
        msg.setInformativeText(f"<b>Classement final :</b><br><pre>{ranking_text}</pre>")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()

    # ======================================================
    # Table results
    # ======================================================
    def _edit_table_results(self, table: Table):
        dialog = EditTableResultsDialog(self, table)

        if not dialog.exec():
            return

        table.results = dialog.results()
        table.finished = True

        # Calcul et application des scores
        self._apply_table_scores(table)

        self.tables_view.set_round(self.current_round)
        self.ranking_view.set_tournament(self.current_tournament)

        if self._all_tables_finished():
            # Recalculer la robustesse après la fin du round
            self.current_tournament.recalculate_robustness()

            if self.current_tournament.can_create_round():
                self.round_controls.set_next_enabled(True)
                # Vérifier les répétitions potentielles
                self._check_repetitions()
            else:
                self._finish_tournament()

        # Notifier pour sauvegarder
        self.tournament_changed.emit()

    def _apply_table_scores(self, table: Table):
        """Applique les scores aux joueurs et affiche le résultat."""
        # Système de points: 1er=4pts, 2ème=3pts, 3ème=2pts, 4ème=1pt
        POINTS_BY_POSITION = {1: 3, 2: 2, 3: 1, 4: 1}

        print(f"\n{'='*50}")
        print(f"TABLE {table.number} - RÉSULTATS")
        print(f"{'='*50}")

        for player in table.players:
            position = table.results.get(player.id, 3)
            points = POINTS_BY_POSITION.get(position, 1)
            player.add_score(points)

            position_label = {1: "🥇 1er", 2: "🥈 2ème", 3: "🥉 3ème", 4: "4ème"}.get(position, f"{position}ème")
            print(f"  {player.name:<20} {position_label:<10} +{points}pts → Total: {player.score}pts")

        print(f"{'='*50}\n")

    # ======================================================
    # Reset tournament
    # ======================================================
    def _reset_tournament(self):
        if not self.current_tournament:
            return

        # Confirmation
        reply = QMessageBox.question(
            self,
            "Réinitialiser le tournoi",
            f"Voulez-vous vraiment réinitialiser le tournoi ?\n\n"
            f"Tous les rounds, résultats et scores seront supprimés.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Reset du tournoi
        self.current_tournament.reset()

        # Créer le premier round
        self.current_tournament.create_round()

        # Rafraîchir l'interface
        self.set_current_round(self.current_tournament)

        # Cacher l'alerte de répétition
        self.round_controls.hide_repetition_warning()

        # Notifier pour sauvegarder
        self.tournament_changed.emit()

    # ======================================================
    # Repetition check & shuffle round
    # ======================================================
    def _check_repetitions(self):
        """Vérifie si la prochaine génération aurait des répétitions."""
        if not self.current_tournament:
            self.round_controls.hide_repetition_warning()
            return

        has_repetitions, rate = self.current_tournament.would_have_repetitions()

        if has_repetitions:
            self.round_controls.show_repetition_warning(rate)
            print(f"\n⚠️  ALERTE: {rate:.0f}% des joueurs se sont déjà affrontés!")
            print("   → Utilisez 'Round varié' pour mélanger différemment.\n")
        else:
            self.round_controls.hide_repetition_warning()

    def _shuffle_round(self):
        """Crée un round en évitant les répétitions d'adversaires."""
        if not self.current_tournament or not self._all_tables_finished():
            return

        if not self.current_tournament.can_create_round():
            self._finish_tournament()
            return

        # Créer le round avec l'algorithme basé sur les adversaires
        self.current_tournament.create_round_by_opponents()
        self.set_current_round(self.current_tournament)

        # Cacher l'alerte
        self.round_controls.hide_repetition_warning()

        print(f"\n🔀 Round varié généré (adversaires non rencontrés privilégiés)\n")

        # Notifier pour sauvegarder
        self.tournament_changed.emit()

    # ======================================================
    # Archive tournament
    # ======================================================
    def _archive_tournament(self):
        """Archive le tournoi terminé."""
        if not self.current_tournament:
            return

        # Confirmation
        reply = QMessageBox.question(
            self,
            "Archiver le tournoi",
            f"Voulez-vous archiver le tournoi '{self.current_tournament.name}' ?\n\n"
            f"Il sera déplacé dans l'historique.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if reply != QMessageBox.Yes:
            return

        # Archiver
        tournament_id = self.current_tournament.id
        self.current_tournament.archive()

        # Notifier pour sauvegarder et retirer de la vue
        self.tournament_changed.emit()
        self.tournament_archived.emit(tournament_id)

        # Réinitialiser l'affichage du dashboard
        self.current_tournament = None
        self.current_round = None
        self.timer.stop()
        self.round_controls.hide_archive_button()

        QMessageBox.information(
            self,
            "Tournoi archivé",
            "Le tournoi a été archivé avec succès.\n"
            "Vous pouvez le retrouver dans l'historique."
        )
