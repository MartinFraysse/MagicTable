from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QMessageBox, QFileDialog, QDialog, QLabel, QPushButton
from PySide6.QtCore import QTimer, Signal, QUrl, Qt
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtMultimedia import QSoundEffect
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
from core.bracket import BracketType, BracketRoundName, get_bracket_final_ranking
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
    # Signal émis quand l'utilisateur quitte volontairement le tournoi
    tournament_quit = Signal(int)
    # Signal interne : données serveur reçues depuis le thread de polling
    _server_data_ready = Signal(object)

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
        self.ranking_view.player_remove_requested.connect(self._remove_player_from_tournament)

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
        # Polling résultats Discord (sync temps réel)
        # =====================
        self._discord_sync_timer = QTimer(self)
        self._discord_sync_timer.setInterval(5000)  # toutes les 5 secondes
        self._discord_sync_timer.timeout.connect(self._poll_discord_results)
        self._discord_sync_fetching = False
        self._server_data_ready.connect(self._apply_server_results)

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

        # Démarrer le polling Discord si serveur configuré
        self._start_discord_sync()

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
                        and len(self.current_tournament.players) >= 4
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
                try:
                    from sync.server_client import notify_round_start_async
                    brk = self._bracket_displayed_round.value
                    notify_round_start_async(self.current_tournament.id, None, self.current_tournament.name, brk)
                except Exception:
                    pass
            return

        if not self.current_round:
            return

        self.timer.start(1000)
        self.round_controls.set_start_enabled(False)

        # Marquer le round comme démarré (IN_PROGRESS)
        self.current_round.start()
        self.tournament_changed.emit()

        # Notifier Discord que le chrono est lancé
        if self.current_tournament:
            try:
                from sync.server_client import notify_round_start_async
                notify_round_start_async(
                    self.current_tournament.id,
                    self.current_round.number,
                    self.current_tournament.name,
                )
            except Exception:
                pass

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

        # Créer le round selon le système d'appariement
        if self.current_tournament.is_swiss_format():
            self.current_tournament.create_round_swiss()
        else:
            result = self.current_tournament.create_round()
            if result is None:
                QMessageBox.critical(
                    self,
                    "Appariement impossible",
                    "Impossible de créer les tables avec le nombre de joueurs actuel."
                )
                return

        prev_round_num = self.current_round.number  # avant set_current_round qui change current_round

        self.set_current_round(self.current_tournament)

        # Cacher l'alerte de répétition
        self.round_controls.hide_repetition_warning()

        # Notifier pour sauvegarder
        self.tournament_changed.emit()

        # Notifier Discord : classement round précédent + nouveaux pairings
        try:
            from sync.server_client import notify_next_round_async
            notify_next_round_async(
                self.current_tournament.id,
                self.current_tournament.to_dict(),
                prev_round_num=prev_round_num,
            )
        except Exception:
            pass

    def _finish_tournament(self):
        """Affiche le classement final quand le tournoi est terminé."""
        tournament = self.current_tournament
        players_by_id = {p.id: p for p in tournament.players}

        # ── 1. Classement Swiss de base ──────────────────────────────
        if tournament.is_1v1_format():
            standings = build_standings(tournament)
            for entry in standings:
                player = players_by_id.get(entry.player_id)
                if player:
                    player.score = entry.match_points
            swiss_ordered = [players_by_id[e.player_id] for e in standings if e.player_id in players_by_id]
        else:
            swiss_ordered = sorted(
                tournament.players,
                key=lambda p: (-p.score, -p.robustness, p.name)
            )

        # ── 2. Classement final : bracket (même partiel) prioritaire sur Swiss ─
        swiss_ids = [p.id for p in swiss_ordered]
        if tournament.bracket:
            final_ids = get_bracket_final_ranking(tournament.bracket, swiss_ids)
        else:
            final_ids = swiss_ids
        players = [players_by_id[pid] for pid in final_ids if pid in players_by_id]
        self.ranking_view.set_final_standings(tournament, final_ids)

        self.round_controls.set_next_enabled(False)

        # Jouer le son de victoire
        if self.victory_sound.source().isValid():
            self.victory_sound.play()

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

        # Identifier l'ancien joueur BYE (avant modification)
        old_bye_table = next(
            (t for t in self.current_round.tables if len(t.players) == 1), None
        )
        old_bye_player = old_bye_table.players[0] if old_bye_table else None

        dialog = EditPairingsDialog(self, self.current_round)
        if not dialog.exec():
            return

        self._snapshot()
        new_tables = dialog.get_updated_tables()

        # Identifier le nouveau joueur BYE
        new_bye_table = next(
            (t for t in new_tables if len(t.players) == 1), None
        )
        new_bye_player = new_bye_table.players[0] if new_bye_table else None

        # Si le BYE a changé de joueur, mettre à jour l'historique
        if (old_bye_player and new_bye_player
                and old_bye_player.id != new_bye_player.id):
            # Annuler l'ancien BYE
            old_bye_player.had_bye = False
            self.current_tournament.bye_history.discard(old_bye_player.id)

            # Appliquer le nouveau BYE
            new_bye_player.had_bye = True
            self.current_tournament.bye_history.add(new_bye_player.id)

        # Appliquer les nouvelles tables
        self.current_round.tables = new_tables

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
                        and len(self.current_tournament.players) >= 4
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
        # Système de points: 1er=3pts, 2ème=2pts, 3ème-4ème=1pt
        POINTS_BY_POSITION = {1: 3, 2: 2, 3: 1, 4: 1}

        for player in table.players:
            position = table.results.get(player.id, 3)
            points = POINTS_BY_POSITION.get(position, 1)
            player.add_score(points)

    def _apply_1v1_standings(self):
        """Recalcule tous les scores 1v1 depuis les résultats bruts (Win=3, Loss=0)."""
        standings = build_standings(self.current_tournament)
        players_by_id = {p.id: p for p in self.current_tournament.players}

        for entry in standings:
            player = players_by_id.get(entry.player_id)
            if player:
                player.score = entry.match_points

        self.current_tournament.calculate_swiss_tiebreakers()

    # ======================================================
    # Bracket (phase d'élimination)
    # ======================================================

    def _launch_bracket(self):
        """Demande le format du bracket puis lance la phase éliminatoire."""
        if not self.current_tournament:
            return

        n = len(self.current_tournament.players)
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
        prev_round_num = self.current_round.number if self.current_round else None
        self.current_tournament.start_bracket(bracket_type)
        self.round_controls.hide_bracket_launch_button()
        self._setup_bracket_mode(self.current_tournament)
        self.tournament_changed.emit()

        # Notifier Discord : classement Swiss final + pairings du 1er round bracket
        try:
            from sync.server_client import notify_next_round_async
            brk_round = self.current_tournament.bracket.current_round_name()
            notify_next_round_async(
                self.current_tournament.id,
                self.current_tournament.to_dict(),
                prev_round_num=prev_round_num,
                new_bracket_round=brk_round.value if brk_round else None,
            )
        except Exception:
            pass

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

        prev_bracket_round = self._bracket_displayed_round  # avant l'avance

        # Calculer les éliminés du round précédent
        players_by_id   = {p.id: p for p in self.current_tournament.players}
        prev_matches    = bracket.get_matches_for_round(prev_bracket_round)
        eliminated_names = []
        for m in prev_matches:
            if m.finished and m.winner_id is not None and not m.is_third_place:
                loser_id = m.player2_id if m.winner_id == m.player1_id else m.player1_id
                if loser_id and m.loser_next_match_id is None:
                    p = players_by_id.get(loser_id)
                    if p:
                        eliminated_names.append(p.name)

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

        # Notifier Discord : classement + nouveaux pairings + éliminations
        try:
            from sync.server_client import notify_next_round_async
            notify_next_round_async(
                self.current_tournament.id,
                self.current_tournament.to_dict(),
                prev_bracket_round=prev_bracket_round.value,
                new_bracket_round=self._bracket_displayed_round.value,
                eliminated_names=eliminated_names,
            )
        except Exception:
            pass

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

        self._snapshot()
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
        self._record_podiums()
        tournament_id = self.current_tournament.id
        self.current_tournament.archive()
        self.tournament_changed.emit()
        self.tournament_archived.emit(tournament_id)
        self._clear_dashboard()

        # Supprimer les canaux Discord du tournoi
        try:
            from sync.server_client import notify_quit_async
            notify_quit_async(tournament_id)
        except Exception:
            pass

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

        # Obtenir le classement final (bracket prioritaire sur Swiss si disponible)
        tournament = self.current_tournament
        players_by_id = {p.id: p for p in tournament.players}

        if tournament.is_1v1_format():
            standings = build_standings(tournament)
            swiss_ordered = [players_by_id[e.player_id] for e in standings if e.player_id in players_by_id]
        else:
            swiss_ordered = sorted(
                tournament.players,
                key=lambda p: (-p.score, -p.robustness, p.name)
            )

        if tournament.bracket:
            swiss_ids = [p.id for p in swiss_ordered]
            final_ids = get_bracket_final_ranking(tournament.bracket, swiss_ids)
            ranked_players = [players_by_id[pid] for pid in final_ids if pid in players_by_id]
        else:
            ranked_players = swiss_ordered

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

        tid = self.current_tournament.id
        self.tournament_changed.emit()
        self._clear_dashboard()
        self.tournament_quit.emit(tid)

        # Notifier le bot Discord pour supprimer les canaux
        try:
            from sync.server_client import notify_quit_async
            notify_quit_async(tid)
        except Exception:
            pass

    def _clear_dashboard(self):
        """Réinitialise l'affichage du dashboard à l'état initial."""
        # Arrêter le timer et le polling Discord
        self.timer.stop()
        self._discord_sync_timer.stop()

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

    # ======================================================
    # Polling résultats Discord (sync temps réel)
    # ======================================================

    def _start_discord_sync(self):
        """Démarre le polling serveur si un serveur est configuré."""
        try:
            from sync.server_client import _load_config
            if not _load_config():
                return
        except Exception:
            return
        if not self._discord_sync_timer.isActive():
            self._discord_sync_timer.start()

    def _poll_discord_results(self):
        """Lance un fetch serveur en background (non-bloquant)."""
        if self._discord_sync_fetching or not self.current_tournament:
            return
        self._discord_sync_fetching = True

        def _fetch():
            try:
                from sync.server_client import fetch
                data = fetch("tournaments")
                if data is not None:
                    self._server_data_ready.emit(data)
            except Exception:
                pass
            finally:
                self._discord_sync_fetching = False

        threading.Thread(target=_fetch, daemon=True).start()

    def _apply_server_results(self, server_tournaments: list):
        """Applique les résultats reçus du serveur si différents de l'état local.
        Appelé sur le thread principal via le signal _server_data_ready."""
        if not self.current_tournament:
            return

        # Trouver le tournoi courant dans les données serveur
        t_dict = next(
            (t for t in server_tournaments if t.get("id") == self.current_tournament.id),
            None
        )
        if not t_dict:
            return

        # ── Mode bracket ───────────────────────────────────────────────────────
        if self._bracket_mode:
            self._apply_server_bracket(t_dict)
            return

        # ── Mode round normal ──────────────────────────────────────────────────
        if not self.current_round:
            return

        # Trouver le round correspondant (même numéro)
        server_rounds = t_dict.get("rounds", [])
        if not server_rounds:
            return
        server_round = next(
            (r for r in server_rounds if r.get("number") == self.current_round.number),
            None
        )
        if not server_round:
            return

        server_tables = {t.get("number"): t for t in server_round.get("tables", [])}
        changed = False

        for table in self.current_round.tables:
            s_table = server_tables.get(table.number)
            if not s_table:
                continue

            server_results = {int(k): v for k, v in s_table.get("results", {}).items()}
            server_game_scores = {int(k): v for k, v in s_table.get("game_scores", {}).items()}
            server_finished = s_table.get("finished", False)

            if (server_results != table.results
                    or server_game_scores != table.game_scores
                    or server_finished != table.finished):
                table.results = server_results
                table.game_scores = server_game_scores
                table.finished = server_finished
                changed = True

        if changed:
            # Recalculer les standings si format 1v1
            if self.current_tournament.is_1v1_format():
                self._apply_1v1_standings()
            # Sauvegarder localement
            self.tournament_changed.emit()
            # Rafraîchir les vues tables et classement
            self.tables_view.set_round(self.current_round)
            self.ranking_view.set_tournament(self.current_tournament)
            # Activer "Round suivant" si toutes les tables sont terminées
            if self._all_tables_finished():
                self.round_controls.set_next_enabled(True)

    def _apply_server_bracket(self, t_dict: dict):
        """Applique les résultats de bracket reçus du serveur (mode bracket actif)."""
        bracket = self.current_tournament.bracket
        if not bracket or not self._bracket_displayed_round:
            return

        server_bracket = t_dict.get("bracket")
        if not server_bracket:
            return

        server_matches = {m["match_id"]: m for m in server_bracket.get("matches", [])}
        changed = False

        for match in bracket.get_matches_for_round(self._bracket_displayed_round):
            s_match = server_matches.get(match.match_id)
            if not s_match:
                continue
            # Appliquer seulement si le serveur a un résultat et qu'on n'en a pas encore
            if s_match.get("finished") and s_match.get("winner_id") is not None and not match.finished:
                bracket.record_result(match.match_id, s_match["winner_id"])
                changed = True

        if changed:
            players_by_id = {p.id: p for p in self.current_tournament.players}
            matches = bracket.get_matches_for_round(self._bracket_displayed_round)
            self.tables_view.set_bracket_round(matches, players_by_id)
            self.ranking_view.set_tournament(self.current_tournament)
            self._update_bracket_tiles()
            self.tournament_changed.emit()

            if self._all_bracket_round_matches_finished():
                self.round_controls.set_next_enabled(True)
                round_order = bracket.get_round_order()
                is_last = self._bracket_displayed_round == round_order[-1]
                self.round_controls.set_finish_mode(is_last)
