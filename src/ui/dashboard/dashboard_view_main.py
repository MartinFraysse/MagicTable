from PySide6.QtWidgets import QWidget, QVBoxLayout, QMessageBox, QFileDialog
from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QShortcut, QKeySequence
import subprocess
import os
import threading

from export.pdf_export import export_tournament_pdf

from ui.dashboard.tiles_view import DashboardTilesView
from ui.dashboard.ranking_view import DashboardRankingView
from ui.dashboard.tables_view import DashboardTablesView
from ui.dashboard.round_controls_view import DashboardRoundControlsView
from ui.dashboard.dialogs.edit_table_results import EditTableResultsDialog
from ui.dashboard.dialogs.edit_pairings_dialog import EditPairingsDialog
from ui.dashboard.dialogs.edit_bracket_result import EditBracketResultDialog
from ui.dashboard.dialogs.launch_bracket_dialog import LaunchBracketDialog
from ui.dashboard.pairings_window import PairingsWindow
from ui.dashboard.final_standings_overlay import FinalStandingsOverlay

from core.tournament import Tournament
from core.tournament_history import TournamentHistory
from core.table import Table
from core.round import Round
from core.bracket import BracketRoundName
from core.ranking import final_ranking, commander_points


class DashboardViewMain(QWidget):
    TABLES_PREFERRED_HEIGHT = 240  # Hauteur préférée pour les tables
    TABLES_MIN_HEIGHT = 220        # Hauteur minimale pour les tables
    RANKING_MIN_HEIGHT = 100       # Hauteur minimale pour le ranking

    # Signal émis quand le tournoi doit être sauvegardé
    tournament_changed = Signal()
    # Signal émis quand le tournoi est archivé (avec l'ID du tournoi)
    tournament_archived = Signal(int)
    # Signal émis quand l'utilisateur quitte volontairement le tournoi
    tournament_quit = Signal(int)
    # Signal interne : données serveur reçues depuis le thread de polling

    def __init__(self, parent=None):
        super().__init__(parent)

        self.current_tournament: Tournament | None = None
        self.current_round: Round | None = None

        # Historique pour l'annulation (undo)
        self._history = TournamentHistory()

        # État du mode bracket
        self._bracket_mode: bool = False
        self._bracket_displayed_round: BracketRoundName | None = None

        # =====================
        # Sons
        # =====================
        _base = os.path.join(os.path.dirname(__file__), "..", "..", "assets", "sounds")
        self._sound_victory = os.path.abspath(os.path.join(_base, "victory.wav"))
        self._sound_timer   = os.path.abspath(os.path.join(_base, "timer_end.wav"))

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
        self.ranking_view.player_remove_requested.connect(self._remove_player_from_tournament)
        self.ranking_view.player_added_to_regulars.connect(lambda _name: self.tournament_changed.emit())

        # === TABLES
        self.tables_view = DashboardTablesView(self)
        root.addWidget(self.tables_view, 0)
        self.tables_view.edit_results_requested.connect(
            self._edit_table_results
        )
        self.tables_view.edit_bracket_result_requested.connect(
            self._edit_bracket_result
        )

        # === CONTROLES
        self.round_controls = DashboardRoundControlsView(self)
        root.addWidget(self.round_controls, 0)

        self.round_controls.set_start_enabled(False)
        self.round_controls.set_next_enabled(False)

        self.round_controls.start_round_requested.connect(self._start_round)
        self.round_controls.next_round_requested.connect(self._next_round)
        self.round_controls.shuffle_round_requested.connect(self._shuffle_round)
        self.round_controls.edit_pairings_requested.connect(self._edit_pairings)
        self.round_controls.reset_requested.connect(self._reset_tournament)
        self.round_controls.archive_requested.connect(self._archive_tournament)
        self.round_controls.export_pdf_requested.connect(self._export_pdf)
        self.round_controls.projection_requested.connect(self._show_projection)
        self.round_controls.quit_requested.connect(self._quit_tournament)
        self.round_controls.launch_bracket_requested.connect(self._launch_bracket)
        self.round_controls.undo_requested.connect(self._undo)

        # Raccourci clavier Ctrl+Z
        undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, self)
        undo_shortcut.activated.connect(self._undo)

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
        # Overlay classement final
        # =====================
        self.final_overlay = FinalStandingsOverlay(self)
        self.final_overlay.dismissed.connect(self._auto_archive)

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
        self.final_overlay.fit_to_parent()

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
    # Son
    # ======================================================
    def _play_sound(self, path: str) -> None:
        """Joue un fichier WAV via subprocess (évite le segfault QSoundEffect/FFmpeg)."""
        if not os.path.exists(path):
            return
        def _run():
            for cmd in (["aplay", path], ["paplay", path], ["afplay", path]):
                try:
                    subprocess.run(cmd, timeout=15, capture_output=True)
                    return
                except FileNotFoundError:
                    continue
                except Exception:
                    return
        threading.Thread(target=_run, daemon=True).start()

    # ======================================================
    # Timer
    # ======================================================
    def _tick(self):
        if self.remaining_seconds <= 0:
            self.timer.stop()
            # Jouer le son de fin de timer
            self._play_sound(self._sound_timer)
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
    def set_current_round(self, tournament: Tournament, timer_minutes: int = None, *, _from_undo: bool = False):
        # Vider l'historique si on change de tournoi
        if not _from_undo and tournament is not self.current_tournament:
            self._history.clear()
            self.round_controls.set_undo_enabled(False)

        # Si le tournoi est en phase de bracket, configurer le mode bracket
        if tournament.bracket and not tournament.bracket.finished:
            self._setup_bracket_mode(tournament, timer_minutes)
            return

        if not tournament.rounds:
            return

        self._bracket_mode = False
        self.current_tournament = tournament
        self.current_round = tournament.rounds[-1]

        # Stocker la durée du timer si fournie
        if timer_minutes is not None:
            self.timer_duration = timer_minutes

        self.timer.stop()
        self._reset_timer(self.timer_duration)

        self.round_controls.set_start_enabled(True)
        self.round_controls.set_next_enabled(False)
        self.round_controls.set_finish_mode(False)

        # Bouton "Modifier les pairings" : visible uniquement au round 1
        # et tant qu'aucune table n'est terminée
        self._update_edit_pairings_visibility()

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

    # ======================================================
    # Undo
    # ======================================================
    def _snapshot(self) -> None:
        """Sauvegarde l'état actuel du tournoi avant une mutation."""
        if self.current_tournament:
            self._history.snapshot(self.current_tournament)
            self.round_controls.set_undo_enabled(True)

    def _undo(self) -> None:
        """Restaure le dernier état sauvegardé du tournoi."""
        if not self._history.can_undo() or not self.current_tournament:
            return

        self._history.undo(self.current_tournament)

        # Rafraîchir complètement l'UI
        self.set_current_round(self.current_tournament, _from_undo=True)

        # Rétablir l'état des boutons selon l'état réel des tables
        if self.current_round and self._all_tables_finished():
            self.round_controls.set_next_enabled(True)
            if self.current_tournament.can_create_round():
                self.round_controls.set_finish_mode(False)
                self._check_repetitions()
            else:
                self.round_controls.set_finish_mode(True)
                if (self.current_tournament.is_1v1_format()
                        and self.current_tournament.player_count >= 4
                        and self.current_tournament.bracket is None):
                    self.round_controls.show_bracket_launch_button()

        self.round_controls.set_undo_enabled(self._history.can_undo())
        self.tournament_changed.emit()

    # ======================================================
    # Round lifecycle
    # ======================================================
    def _start_round(self):
        # Mode bracket : current_round est None, on démarre quand même le chrono
        if self._bracket_mode:
            if self.current_tournament and self._bracket_displayed_round:
                self.timer.start(1000)
                self.round_controls.set_start_enabled(False)
                # Marquer le round bracket comme démarré
                self.current_tournament.bracket.started_round = self._bracket_displayed_round.value
                self.tournament_changed.emit()
            return

        if not self.current_round:
            return

        self.timer.start(1000)
        self.round_controls.set_start_enabled(False)

        # Marquer le round comme démarré (IN_PROGRESS)
        self.current_round.start()
        self.tournament_changed.emit()

    def _all_tables_finished(self) -> bool:
        return (
            self.current_round is not None
            and self.current_round.tables is not None
            and all(table.finished for table in self.current_round.tables)
        )

    def _all_bracket_round_matches_finished(self) -> bool:
        """Vérifie si tous les matches du round de bracket affiché sont terminés."""
        bracket = self.current_tournament.bracket if self.current_tournament else None
        if not bracket or not self._bracket_displayed_round:
            return False
        matches = bracket.get_matches_for_round(self._bracket_displayed_round)
        return bool(matches) and all(m.finished for m in matches)

    def _next_round(self):
        if not self.current_tournament:
            return

        # Mode bracket
        if self._bracket_mode:
            if not self._all_bracket_round_matches_finished():
                return
            self._advance_bracket_round()
            return

        # Mode normal
        if not self._all_tables_finished():
            return

        if not self.current_tournament.can_create_round():
            self.round_controls.hide_bracket_launch_button()
            self._finish_tournament()
            return

        self._snapshot()

        # Synchroniser les scores 1v1 avant le pairing
        if self.current_tournament.is_1v1_format():
            self._apply_1v1_standings()

        # Swiss pour les formats 1v1, tables 3-4 pour le Commander
        if self.current_tournament.create_round() is None:
            QMessageBox.critical(
                self,
                "Appariement impossible",
                "Impossible de créer les tables avec le nombre de joueurs actuel."
            )
            return

        self.set_current_round(self.current_tournament)

        # Cacher l'alerte de répétition
        self.round_controls.hide_repetition_warning()

        # Notifier pour sauvegarder
        self.tournament_changed.emit()

    def _finish_tournament(self):
        """Affiche le classement final quand le tournoi est terminé."""
        tournament = self.current_tournament
        tournament.finish_last_round()

        # Scores 1v1 à jour (match points) avant le classement final
        if tournament.is_1v1_format():
            self._apply_1v1_standings()

        # Classement final : bracket (même partiel) prioritaire sur les rondes
        players = final_ranking(tournament)
        self.ranking_view.set_final_standings(tournament, [p.id for p in players])

        self.round_controls.set_next_enabled(False)

        # Jouer le son de victoire
        self._play_sound(self._sound_victory)

        # Overlay de fin de tournoi (superposé au dashboard, pas de nouvelle fenêtre)
        self.final_overlay.show_standings(self.current_tournament.name, players)

    # ======================================================
    # Edit pairings (round 1 only)
    # ======================================================
    def _update_edit_pairings_visibility(self):
        """Affiche le bouton 'Modifier les pairings' uniquement au round 1 sans résultat."""
        if not self.current_round:
            self.round_controls.set_edit_pairings_visible(False)
            return

        is_round_1 = self.current_round.number == 1
        # Exclure les tables BYE (1 joueur) qui sont finished dès leur création
        real_tables = [t for t in (self.current_round.tables or []) if len(t.players) > 1]
        any_finished = any(t.finished for t in real_tables)
        self.round_controls.set_edit_pairings_visible(is_round_1 and not any_finished)

    def _edit_pairings(self):
        """Ouvre le dialog de modification manuelle des pairings (round 1)."""
        if not self.current_round or self.current_round.number != 1:
            return

        dialog = EditPairingsDialog(self, self.current_round)
        if not dialog.exec():
            return

        self._snapshot()
        new_tables = dialog.get_updated_tables()

        # Appliquer les nouvelles tables (l'historique des byes suit les tables)
        self.current_round.tables = new_tables
        self.current_tournament.sync_byes()

        # Recalculer les scores si format 1v1 (le BYE compte comme victoire)
        if self.current_tournament.is_1v1_format():
            self._apply_1v1_standings()

        # Rafraîchir l'affichage
        self.tables_view.set_round(self.current_round)
        self.ranking_view.set_tournament(self.current_tournament)
        self._update_projection()
        self.tournament_changed.emit()

    # ======================================================
    # Table results
    # ======================================================
    def _edit_table_results(self, table: Table):
        if self.current_round and self.current_round.state.value == "preparation":
            QMessageBox.warning(
                self,
                "Round non démarré",
                "Lance le chrono avant d'entrer les résultats."
            )
            return
        dialog = EditTableResultsDialog(self, table)

        if not dialog.exec():
            return

        self._snapshot()
        table.results = dialog.results()
        table.game_scores = dialog.game_scores()
        table.finished = True

        # Calcul et application des scores
        if self.current_tournament.is_1v1_format():
            self._apply_1v1_standings()
        else:
            self._apply_table_scores(table)

        self.tables_view.set_round(self.current_round)
        self.ranking_view.set_tournament(self.current_tournament)
        self._update_projection()
        self._update_edit_pairings_visibility()

        if self._all_tables_finished():
            if not self.current_tournament.is_1v1_format():
                # Recalculer la robustesse après la fin du round (Commander uniquement)
                self.current_tournament.recalculate_robustness()

            self.round_controls.set_next_enabled(True)

            if self.current_tournament.can_create_round():
                self.round_controls.set_finish_mode(False)
                self._check_repetitions()
            else:
                self.round_controls.set_finish_mode(True)
                # Proposer le bracket pour les formats 1v1 (pas déjà en cours)
                if (self.current_tournament.is_1v1_format()
                        and self.current_tournament.player_count >= 4
                        and self.current_tournament.bracket is None):
                    self.round_controls.show_bracket_launch_button()

        # Notifier pour sauvegarder
        self.tournament_changed.emit()

    # ======================================================
    # Drop player from tournament (abandon / forfait)
    # ======================================================
    def _remove_player_from_tournament(self, player_id: int):
        if not self.current_tournament:
            return

        player = next((p for p in self.current_tournament.players if p.id == player_id), None)
        if not player:
            return

        if player.dropped:
            QMessageBox.information(
                self, "Abandon",
                f"« {player.name} » a déjà abandonné le tournoi."
            )
            return

        reply = QMessageBox.question(
            self,
            "Abandon du joueur",
            f"Marquer « {player.name} » comme abandon ?\n\n"
            "Il conserve ses résultats passés mais ne participera plus aux rounds suivants.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self._snapshot()
        # Marquer comme droppé
        player.dropped = True
        dropped_ids = {p.id for p in self.current_tournament.players if p.dropped}

        bracket = self.current_tournament.bracket

        if bracket:
            # ── Phase bracket : auto-forfait des matchs impliquant ce joueur ──
            resolved = bracket.auto_resolve_dropped(dropped_ids)
            if resolved:
                self._refresh_bracket_ui()
                # Vérifier si tous les matchs du round bracket sont terminés
                if self._all_bracket_round_matches_finished():
                    self.round_controls.set_next_enabled(True)
                    round_order = bracket.get_round_order()
                    is_last = self._bracket_displayed_round == round_order[-1]
                    self.round_controls.set_finish_mode(is_last)
        else:
            # ── Phase Swiss : gérer le round en cours ─────────────────────────
            if self.current_round and self.current_round.tables:
                for table in self.current_round.tables:
                    if player not in table.players or table.finished:
                        continue

                    if len(table.players) == 2:
                        # 1v1 : victoire par forfait pour l'adversaire
                        other = next(p for p in table.players if p.id != player_id)
                        table.results = {other.id: 1, player_id: 2}
                        table.game_scores = {other.id: 2, player_id: 0}
                        table.finished = True
                    elif len(table.players) >= 3:
                        # Commander : dernière place automatique, les autres continuent
                        n = len(table.players)
                        table.results[player_id] = n
                    break

            # Recalculer les scores
            if self.current_tournament.is_1v1_format():
                self._apply_1v1_standings()
            else:
                self.current_tournament.recalculate_robustness()

            if self.current_round:
                self.tables_view.set_round(self.current_round)

            # Vérifier si tous les matchs Swiss sont maintenant terminés
            if self.current_round and self._all_tables_finished():
                if not self.current_tournament.is_1v1_format():
                    self.current_tournament.recalculate_robustness()
                self.round_controls.set_next_enabled(True)
                if self.current_tournament.can_create_round():
                    self.round_controls.set_finish_mode(False)
                else:
                    self.round_controls.set_finish_mode(True)

        self.ranking_view.set_tournament(self.current_tournament)
        self._update_projection()
        self.tournament_changed.emit()

    def _refresh_bracket_ui(self):
        """Rafraîchit l'affichage du bracket après un changement."""
        bracket = self.current_tournament.bracket
        if not bracket or not self._bracket_displayed_round:
            return
        players_by_id = {p.id: p for p in self.current_tournament.players}
        matches = bracket.get_matches_for_round(self._bracket_displayed_round)
        self.tables_view.set_bracket_round(matches, players_by_id)
        self.ranking_view.set_tournament(self.current_tournament)
        self._update_bracket_tiles()

    def _apply_table_scores(self, table: Table):
        """Applique les scores aux joueurs et affiche le résultat."""
        for player in table.players:
            player.add_score(commander_points(table.results.get(player.id, 3)))

    def _apply_1v1_standings(self):
        """Recalcule tous les scores 1v1 depuis les résultats bruts (Win=3, Draw=1, Loss=0)."""
        self.current_tournament.sync_match_points()

    # ======================================================
    # Bracket (phase d'élimination)
    # ======================================================

    def _launch_bracket(self):
        """Demande le format du bracket puis lance la phase éliminatoire."""
        if not self.current_tournament:
            return

        n = self.current_tournament.player_count  # joueurs actifs (hors abandons)
        if n < 2:
            QMessageBox.warning(self, "Bracket", "Pas assez de joueurs pour lancer un bracket.")
            return

        dialog = LaunchBracketDialog(self, player_count=n)
        if not dialog.exec():
            return

        bracket_type = dialog.bracket_type()
        if bracket_type is None:
            return

        self._snapshot()
        self.current_tournament.start_bracket(bracket_type)
        self.round_controls.hide_bracket_launch_button()
        self._setup_bracket_mode(self.current_tournament)
        self.tournament_changed.emit()

    def _setup_bracket_mode(self, tournament: Tournament, timer_minutes: int = None):
        """Configure l'UI en mode bracket d'élimination."""
        self.current_tournament = tournament
        self.current_round = None
        self._bracket_mode = True

        bracket = tournament.bracket
        self._bracket_displayed_round = bracket.current_round_name()

        if timer_minutes is not None:
            self.timer_duration = timer_minutes

        self.timer.stop()
        self._reset_timer(self.timer_duration)

        self.round_controls.set_bracket_mode()
        self.round_controls.set_start_enabled(True)
        self.round_controls.set_next_enabled(False)

        # Vérifier si le round affiché est déjà terminé (reprise en cours de route)
        if self._all_bracket_round_matches_finished():
            self.round_controls.set_next_enabled(True)

        # Dernier round du bracket ?
        round_order = bracket.get_round_order()
        is_last = self._bracket_displayed_round == round_order[-1]
        self.round_controls.set_finish_mode(is_last)

        players_by_id = {p.id: p for p in tournament.players}
        matches = bracket.get_matches_for_round(self._bracket_displayed_round) if self._bracket_displayed_round else []

        self.tables_view.title.setText("🏆 Phase éliminatoire")
        self.tables_view.set_bracket_round(matches, players_by_id)
        self.ranking_view.set_tournament(tournament)
        self._update_bracket_tiles()
        self._recompute_layout_heights()

    def _update_bracket_tiles(self):
        ROUND_LABELS = {
            "quart": "Quarts de finale",
            "demi": "Demi-finales",
            "final": "Finales",
        }
        round_val = self._bracket_displayed_round.value if self._bracket_displayed_round else "?"
        label = ROUND_LABELS.get(round_val, round_val)

        bracket = self.current_tournament.bracket
        matches = bracket.get_matches_for_round(self._bracket_displayed_round) if self._bracket_displayed_round else []
        real_matches = [m for m in matches if m.player1_id is not None and m.player2_id is not None]

        self.tiles_view.set_active()
        self.tiles_view.tile_name.value_label.setText(self.current_tournament.name)
        self.tiles_view.tile_round.value_label.setText(label)
        self.tiles_view.tile_players.value_label.setText(str(len(self.current_tournament.players)))
        self.tiles_view.tile_tables.value_label.setText(str(len(real_matches)))

    def _edit_bracket_result(self, match):
        """Saisit ou modifie le résultat d'un match de bracket."""
        if not self.current_tournament:
            return
        bracket = self.current_tournament.bracket
        if not bracket:
            return
        if (self._bracket_displayed_round is not None
                and bracket.started_round != self._bracket_displayed_round.value):
            QMessageBox.warning(
                self,
                "Round non démarré",
                "Lance le chrono avant d'entrer les résultats."
            )
            return
        players_by_id = {p.id: p for p in self.current_tournament.players}

        dialog = EditBracketResultDialog(self, match, players_by_id)
        if not dialog.exec():
            return

        winner_id = dialog.winner_id()
        if winner_id is None:
            return

        # Si le match était déjà terminé, annuler le résultat (cascade) avant de ré-enregistrer
        if match.finished:
            bracket.reset_result(match.match_id)

        bracket.record_result(match.match_id, winner_id)
        # Résoudre les matchs devenus injouables (slot qui ne sera jamais rempli, abandon)
        bracket.auto_resolve_dropped({p.id for p in self.current_tournament.players if p.dropped})

        # Rafraîchir les cartes du round actuel
        matches = bracket.get_matches_for_round(self._bracket_displayed_round)
        self.tables_view.set_bracket_round(matches, players_by_id)
        self.ranking_view.set_tournament(self.current_tournament)
        self._update_bracket_tiles()

        # Mettre à jour l'état du bouton selon que tous les matches sont terminés ou non
        if self._all_bracket_round_matches_finished():
            self.round_controls.set_next_enabled(True)
            round_order = bracket.get_round_order()
            is_last = self._bracket_displayed_round == round_order[-1]
            self.round_controls.set_finish_mode(is_last)
        else:
            self.round_controls.set_next_enabled(False)

        self.tournament_changed.emit()

    def _advance_bracket_round(self):
        """Passe au round suivant du bracket (demi, finale…)."""
        bracket = self.current_tournament.bracket
        round_order = bracket.get_round_order()
        current_idx = round_order.index(self._bracket_displayed_round)

        if current_idx + 1 >= len(round_order):
            # Était le dernier round (Finale) — terminer
            self._finish_tournament()
            return

        players_by_id = {p.id: p for p in self.current_tournament.players}

        self._bracket_displayed_round = round_order[current_idx + 1]
        # Réinitialiser le flag "démarré" pour le nouveau round
        self.current_tournament.bracket.started_round = None
        matches = bracket.get_matches_for_round(self._bracket_displayed_round)

        self.tables_view.set_bracket_round(matches, players_by_id)
        self._update_bracket_tiles()

        self.round_controls.set_start_enabled(True)
        self.round_controls.set_next_enabled(False)

        round_order = bracket.get_round_order()
        is_last = self._bracket_displayed_round == round_order[-1]
        self.round_controls.set_finish_mode(is_last)

        self.tournament_changed.emit()

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
            "Voulez-vous vraiment réinitialiser le tournoi ?\n\n"
            "Tous les rounds, résultats et scores seront supprimés.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        self._snapshot()
        # Reset du tournoi
        self.current_tournament.reset()

        # Créer le premier round avec l'algorithme approprié
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
        else:
            self.round_controls.hide_repetition_warning()

    def _shuffle_round(self):
        """Crée un round en évitant les répétitions d'adversaires."""
        if not self.current_tournament or not self._all_tables_finished():
            return

        if not self.current_tournament.can_create_round():
            self._finish_tournament()
            return

        self._snapshot()
        # Créer le round avec l'algorithme basé sur les adversaires
        self.current_tournament.create_round_by_opponents()
        self.set_current_round(self.current_tournament)

        # Cacher l'alerte
        self.round_controls.hide_repetition_warning()

        # Notifier pour sauvegarder
        self.tournament_changed.emit()

    # ======================================================
    # Archive tournament
    # ======================================================
    def _auto_archive(self):
        """Archive automatiquement le tournoi quand l'overlay de fin est fermé."""
        if not self.current_tournament:
            return
        tournament_id = self.current_tournament.id
        self.current_tournament.archive()
        self.tournament_changed.emit()
        self.tournament_archived.emit(tournament_id)
        self._clear_dashboard()

    def _archive_tournament(self):
        """Archive le tournoi terminé (bouton manuel, garde pour compatibilité)."""
        self._auto_archive()

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

        tid = self.current_tournament.id
        self.tournament_changed.emit()
        self._clear_dashboard()
        self.tournament_quit.emit(tid)

    def _clear_dashboard(self):
        """Réinitialise l'affichage du dashboard à l'état initial."""
        # Arrêter le timer
        self.timer.stop()

        # Vider l'historique undo
        self._history.clear()

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
        self.round_controls.set_undo_enabled(False)
        self.round_controls.hide_repetition_warning()
        self.round_controls.hide_archive_button()

        # Cacher l'overlay de fin de tournoi si visible
        self.final_overlay.hide()

        # Fermer la fenêtre de projection si ouverte
        if self.pairings_window:
            self.pairings_window.close()
