from PySide6.QtWidgets import QWidget, QVBoxLayout, QSpacerItem, QMessageBox, QFileDialog
from PySide6.QtCore import QTimer, Signal, QUrl
from PySide6.QtMultimedia import QSoundEffect
import os

from export.pdf_export import export_tournament_pdf

from ui.dashboard.tiles_view import DashboardTilesView
from ui.dashboard.ranking_view import DashboardRankingView
from ui.dashboard.tables_view import DashboardTablesView
from ui.dashboard.round_controls_view import DashboardRoundControlsView
from ui.dashboard.dialogs.edit_table_results import EditTableResultsDialog
from ui.dashboard.pairings_window import PairingsWindow

from core.tournament import Tournament
from core.table import Table
from core.round import Round
from core.regular_player import RegularPlayer
from core.standings import build_standings
from storage.regular_players import RegularPlayerStorage


class DashboardViewMain(QWidget):
    TABLES_PREFERRED_HEIGHT = 240  # Hauteur préférée pour les tables
    TABLES_MIN_HEIGHT = 220        # Hauteur minimale pour les tables
    RANKING_MIN_HEIGHT = 100       # Hauteur minimale pour le ranking

    # Signal émis quand le tournoi doit être sauvegardé
    tournament_changed = Signal()
    # Signal émis quand le tournoi est archivé (avec l'ID du tournoi)
    tournament_archived = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.current_tournament: Tournament | None = None
        self.current_round: Round | None = None

        # =====================
        # Son de fin de tournoi
        # =====================
        self.victory_sound = QSoundEffect(self)
        sound_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "assets", "sounds", "victory.wav"
        )
        if os.path.exists(sound_path):
            self.victory_sound.setSource(QUrl.fromLocalFile(os.path.abspath(sound_path)))
            self.victory_sound.setVolume(0.8)

        # Son de fin de timer
        self.timer_sound = QSoundEffect(self)
        timer_sound_path = os.path.join(
            os.path.dirname(__file__),
            "..", "..", "assets", "sounds", "timer_end.wav"
        )
        if os.path.exists(timer_sound_path):
            self.timer_sound.setSource(QUrl.fromLocalFile(os.path.abspath(timer_sound_path)))
            self.timer_sound.setVolume(1.0)

        # =====================
        # Layout
        # =====================
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(0, 0, 0, 0)

        # === TUILES (hauteur naturelle)
        self.tiles_view = DashboardTilesView(self)
        root.addWidget(self.tiles_view, 0)

        # === CLASSEMENT
        self.ranking_view = DashboardRankingView(self)
        root.addWidget(self.ranking_view, 0)

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
        self.round_controls.export_pdf_requested.connect(self._export_pdf)
        self.round_controls.projection_requested.connect(self._show_projection)
        self.round_controls.quit_requested.connect(self._quit_tournament)

        # =====================
        # Timer
        # =====================
        self.timer_duration = 50  # Durée par défaut en minutes
        self.remaining_seconds = self.timer_duration * 60
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

        # =====================
        # Fenêtre de projection
        # =====================
        self.pairings_window: PairingsWindow | None = None

        # =====================
        # Calcul initial des hauteurs
        # =====================
        self._recompute_layout_heights()

    # ======================================================
    # Layout sizing logic
    # ======================================================
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._recompute_layout_heights()

    def _recompute_layout_heights(self):
        # 3 spacings entre les 4 widgets (tiles, ranking, tables, controls)
        spacing = 16 * 3

        tiles_h = self.tiles_view.sizeHint().height()
        controls_h = self.round_controls.sizeHint().height()

        # Utiliser la hauteur réelle du widget
        current_height = self.height() if self.height() > 100 else 880

        available = (
            current_height
            - tiles_h
            - controls_h
            - spacing
        )

        # Priorité aux tables : elles gardent leur taille préférée
        # Le ranking absorbe la réduction en premier
        tables_h = self.TABLES_PREFERRED_HEIGHT
        ranking_h = available - tables_h

        # Si le ranking devient trop petit, réduire les tables
        if ranking_h < self.RANKING_MIN_HEIGHT:
            ranking_h = self.RANKING_MIN_HEIGHT
            tables_h = available - ranking_h

        # Garantir la taille minimale des tables
        if tables_h < self.TABLES_MIN_HEIGHT:
            tables_h = self.TABLES_MIN_HEIGHT

        self.ranking_view.setMinimumHeight(ranking_h)
        self.ranking_view.setMaximumHeight(ranking_h)
        self.tables_view.setMinimumHeight(tables_h)
        self.tables_view.setMaximumHeight(tables_h)

    # ======================================================
    # Timer
    # ======================================================
    def _tick(self):
        if self.remaining_seconds <= 0:
            self.timer.stop()
            # Jouer le son de fin de timer
            if self.timer_sound.source().isValid():
                self.timer_sound.play()
            return

        self.remaining_seconds -= 1
        m = self.remaining_seconds // 60
        s = self.remaining_seconds % 60
        self.tiles_view.set_timer_text(f"{m:02d}:{s:02d}")

        # Synchroniser avec la fenêtre de projection
        if self.pairings_window and self.pairings_window.isVisible():
            self.pairings_window.set_remaining_seconds(self.remaining_seconds)

    def _reset_timer(self, minutes: int = 50):
        self.remaining_seconds = minutes * 60
        self.tiles_view.set_timer_text(f"{minutes:02d}:00")

    # ======================================================
    # Round lifecycle
    # ======================================================
    def set_current_round(self, tournament: Tournament, timer_minutes: int = None):
        if not tournament.rounds:
            return

        self.current_tournament = tournament
        self.current_round = tournament.rounds[-1]

        # Stocker la durée du timer si fournie
        if timer_minutes is not None:
            self.timer_duration = timer_minutes

        self.timer.stop()
        self._reset_timer(self.timer_duration)

        self.round_controls.set_start_enabled(True)
        self.round_controls.set_next_enabled(False)

        # Configurer le mode d'affichage du ranking
        self.round_controls.set_swiss_mode(tournament.is_swiss_format())
        self.ranking_view.set_1v1_mode(tournament.is_1v1_format())

        self.ranking_view.set_tournament(tournament)

        # Compter les tables réelles (exclure les byes pour le compte)
        real_tables = [t for t in (self.current_round.tables or []) if len(t.players) > 1]

        self.tiles_view.update_for_tournament(
            name=tournament.name,
            round_number=self.current_round.number,
            max_rounds=tournament.max_rounds,
            player_count=len(tournament.players),
            table_count=len(real_tables),
        )

        self.tables_view.set_round(self.current_round)

        # Mettre à jour la fenêtre de projection si ouverte
        self._update_projection()

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
            and self.current_round.tables is not None
            and all(table.finished for table in self.current_round.tables)
        )

    def _next_round(self):
        if not self.current_tournament or not self._all_tables_finished():
            return

        if not self.current_tournament.can_create_round():
            self._finish_tournament()
            return

        # Synchroniser les scores 1v1 avant le pairing
        if self.current_tournament.is_1v1_format():
            self._apply_1v1_standings()

        # Utiliser l'algorithme approprié selon le système d'appariement
        if self.current_tournament.is_swiss_format():
            self.current_tournament.create_round_swiss()
            print(f"\n⚖️ Round Swiss généré (appariement officiel)\n")
        else:
            self.current_tournament.create_round()

        self.set_current_round(self.current_tournament)

        # Cacher l'alerte de répétition
        self.round_controls.hide_repetition_warning()

        # Notifier pour sauvegarder
        self.tournament_changed.emit()

    def _finish_tournament(self):
        """Affiche le classement final quand le tournoi est terminé."""
        # Utiliser le tri approprié selon le format
        if self.current_tournament.is_1v1_format():
            standings = build_standings(self.current_tournament)
            # Synchroniser player.score
            players_by_id = {p.id: p for p in self.current_tournament.players}
            for entry in standings:
                player = players_by_id.get(entry.player_id)
                if player:
                    player.score = entry.match_points
            players = [players_by_id[e.player_id] for e in standings if e.player_id in players_by_id]
        else:
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

        # Jouer le son de victoire
        if self.victory_sound.source().isValid():
            self.victory_sound.play()

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
        if self.current_tournament.is_1v1_format():
            self._apply_1v1_standings()
        else:
            self._apply_table_scores(table)

        self.tables_view.set_round(self.current_round)
        self.ranking_view.set_tournament(self.current_tournament)
        self._update_projection()

        if self._all_tables_finished():
            if not self.current_tournament.is_1v1_format():
                # Recalculer la robustesse après la fin du round (Commander uniquement)
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

    def _apply_1v1_standings(self):
        """Recalcule tous les scores 1v1 depuis les résultats bruts (Win=3, Loss=0)."""
        standings = build_standings(self.current_tournament)
        players_by_id = {p.id: p for p in self.current_tournament.players}

        for entry in standings:
            player = players_by_id.get(entry.player_id)
            if player:
                player.score = entry.match_points

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

        # Réinitialiser l'historique des byes pour Swiss
        self.current_tournament.bye_history.clear()

        # Créer le premier round avec l'algorithme approprié
        if self.current_tournament.is_swiss_format():
            self.current_tournament.create_round_swiss()
        else:
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

        # En mode Swiss, pas besoin de vérifier les répétitions
        # (le système Swiss évite nativement les rematches)
        if self.current_tournament.is_swiss_format():
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

        # Enregistrer les podiums pour les joueurs réguliers
        self._record_podiums()

        # Archiver
        tournament_id = self.current_tournament.id
        self.current_tournament.archive()

        # Notifier pour sauvegarder et retirer de la vue
        self.tournament_changed.emit()
        self.tournament_archived.emit(tournament_id)

        # Réinitialiser l'affichage du dashboard
        self._clear_dashboard()

        QMessageBox.information(
            self,
            "Tournoi archivé",
            "Le tournoi a été archivé avec succès.\n"
            "Vous pouvez le retrouver dans l'historique."
        )

    def _export_pdf(self):
        """Exporte les résultats du tournoi en PDF."""
        if not self.current_tournament:
            return

        # Nom de fichier par défaut
        default_name = f"{self.current_tournament.name.replace(' ', '_')}_{self.current_tournament.date.replace('/', '-')}.pdf"

        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter en PDF",
            default_name,
            "Fichiers PDF (*.pdf)"
        )

        if not filepath:
            return

        # Ajouter l'extension si manquante
        if not filepath.endswith('.pdf'):
            filepath += '.pdf'

        success = export_tournament_pdf(self.current_tournament, filepath)

        if success:
            QMessageBox.information(
                self,
                "Export réussi",
                f"Le tournoi a été exporté vers :\n{filepath}"
            )
        else:
            QMessageBox.warning(
                self,
                "Erreur d'export",
                "Une erreur est survenue lors de l'export.\n"
                "Vérifiez que fpdf2 est installé :\n"
                "pip install fpdf2"
            )

    # ======================================================
    # Projection
    # ======================================================
    def _show_projection(self):
        """Ouvre la fenêtre de projection des pairings."""
        if not self.current_round:
            QMessageBox.warning(
                self,
                "Aucun round",
                "Veuillez d'abord lancer un tournoi."
            )
            return

        # Créer la fenêtre si elle n'existe pas
        if not self.pairings_window:
            self.pairings_window = PairingsWindow()

        # Mettre à jour le contenu
        self.pairings_window.set_round(self.current_round)
        self.pairings_window.set_remaining_seconds(self.remaining_seconds)

        # Afficher la fenêtre
        self.pairings_window.show()
        self.pairings_window.raise_()
        self.pairings_window.activateWindow()

    def _update_projection(self):
        """Met à jour la fenêtre de projection si elle est ouverte."""
        if self.pairings_window and self.pairings_window.isVisible():
            self.pairings_window.set_round(self.current_round)

    def _record_podiums(self):
        """Enregistre les résultats du tournoi pour les joueurs réguliers.

        Met à jour pour chaque joueur régulier participant :
        - tournaments_played (+1)
        - points (+score du tournoi)
        - top_1/top_2/top_3 si le joueur est sur le podium
        """
        if not self.current_tournament:
            return

        # Éviter les doublons
        if self.current_tournament.podiums_recorded:
            return

        # Charger les joueurs réguliers
        raw = RegularPlayerStorage.load()
        regular_players = [RegularPlayer.from_dict(d) for d in raw]
        regular_by_pseudo = {p.pseudo.lower().strip(): p for p in regular_players}

        # Obtenir le classement
        ranked_players = sorted(
            self.current_tournament.players,
            key=lambda p: (-p.score, -p.robustness, p.name)
        )

        # Enregistrer les participations, points et podiums
        players_updated = False
        for rank, player in enumerate(ranked_players, 1):
            pseudo_lower = player.name.lower().strip()
            if pseudo_lower in regular_by_pseudo:
                regular_player = regular_by_pseudo[pseudo_lower]
                # Incrémenter le nombre de tournois joués
                regular_player.tournaments_played += 1
                # Ajouter les points du tournoi
                regular_player.points += player.score
                players_updated = True
                # Ajouter le podium si top 3
                if rank <= 3:
                    regular_player.add_top(rank)

        # Sauvegarder si des joueurs ont été mis à jour
        if players_updated:
            RegularPlayerStorage.save([p.to_dict() for p in regular_players])
            self.current_tournament.podiums_recorded = True

    # ======================================================
    # Quit tournament
    # ======================================================
    def _quit_tournament(self):
        """Quitte le tournoi et réinitialise le dashboard."""
        if not self.current_tournament:
            return

        # Confirmation
        reply = QMessageBox.question(
            self,
            "Quitter le tournoi",
            f"Voulez-vous quitter le tournoi '{self.current_tournament.name}' ?\n\n"
            f"Le tournoi sera conservé et pourra être relancé depuis les tournois.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Sauvegarder l'état actuel
        self.tournament_changed.emit()

        # Réinitialiser l'affichage
        self._clear_dashboard()

    def _clear_dashboard(self):
        """Réinitialise l'affichage du dashboard à l'état initial."""
        # Arrêter le timer
        self.timer.stop()

        # Réinitialiser les références
        self.current_tournament = None
        self.current_round = None

        # Réinitialiser les tiles
        self.tiles_view.reset()

        # Vider le classement
        self.ranking_view.set_tournament(None)

        # Vider les tables
        self.tables_view.set_round(None)

        # Réinitialiser les contrôles
        self.round_controls.set_start_enabled(False)
        self.round_controls.set_next_enabled(False)
        self.round_controls.hide_repetition_warning()
        self.round_controls.hide_archive_button()

        # Fermer la fenêtre de projection si ouverte
        if self.pairings_window:
            self.pairings_window.close()
