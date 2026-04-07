from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem,
    QHeaderView, QSizePolicy,
    QMenu, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from core.regular_player import RegularPlayer
from core.standings import build_standings
from storage.regular_players import RegularPlayerStorage
from ui.dashboard.dialogs.round_summary_dialog import RoundSummaryDialog


class DashboardRankingView(QFrame):
    # Signal émis quand un joueur est ajouté aux joueurs permanents
    player_added_to_regulars = Signal(str)  # pseudo du joueur
    # Signal émis quand on veut retirer un joueur du tournoi
    player_remove_requested = Signal(int)   # player_id

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("DashboardCard")

        self._tournament = None
        self._previous_ranks = {}  # player_id -> rank at previous round
        self._swiss_mode = False
        self._1v1_mode = False

        # =====================
        # Layout
        # =====================
        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        title = QLabel("🏆 Aperçu du classement")
        title.setObjectName("DashboardSectionTitle")
        layout.addWidget(title)

        table = QTableWidget(0, 3)
        table.setObjectName("DashboardTable")

        # --- Structure ---
        table.setHorizontalHeaderLabels(["#", "Joueur", "Score"])
        table.verticalHeader().setVisible(False)

        # --- Comportement ---
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setFocusPolicy(Qt.NoFocus)

        # --- Apparence ---
        table.setShowGrid(False)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # --- Header sizing ---
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        # ✅ Centrage des EN-TÊTES
        for i in range(table.columnCount()):
            h_item = table.horizontalHeaderItem(i)
            if h_item:
                h_item.setTextAlignment(Qt.AlignCenter)

        # --- Size policy ---
        table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # --- Context menu ---
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(self._show_context_menu)

        layout.addWidget(table, 1)

        self.ranking_table = table
        self.ranking_viewport = table.viewport()

        self._player_ids_by_row = {}

    # =================================================
    # Public API
    # =================================================
    def set_swiss_mode(self, enabled: bool):
        """Configure l'affichage pour le mode Swiss (Commander multiplayer)."""
        self._swiss_mode = enabled
        if self._1v1_mode:
            return  # Le mode 1v1 prend le dessus
        self._apply_column_layout()

    def set_1v1_mode(self, enabled: bool):
        """Configure l'affichage pour les formats 1v1 (avec OMW%)."""
        self._1v1_mode = enabled
        self._apply_column_layout()

    def _apply_column_layout(self):
        """Applique la configuration de colonnes selon le mode actif."""
        table = self.ranking_table

        # Vider les lignes AVANT de changer les colonnes pour éviter
        # que Qt accède à des cellules inexistantes (segfault)
        table.setRowCount(0)
        self._player_ids_by_row = {}

        if self._1v1_mode:
            table.setColumnCount(6)
            table.setHorizontalHeaderLabels(["#", "Joueur", "Score", "OMW%", "GW%", "W-L-D"])

            header = table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(5, QHeaderView.ResizeToContents)

        elif self._swiss_mode:
            table.setColumnCount(5)
            table.setHorizontalHeaderLabels(["#", "Joueur", "Score", "Buchholz", "SOS"])

            header = table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        else:
            # Commander standard : score + robustesse comme départage
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(["#", "Joueur", "Score", "Robustesse"])

            header = table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

        # Centrer les en-têtes
        for i in range(table.columnCount()):
            h_item = table.horizontalHeaderItem(i)
            if h_item:
                h_item.setTextAlignment(Qt.AlignCenter)

    def set_tournament(self, tournament):
        table = self.ranking_table
        self._tournament = tournament

        if not tournament:
            table.setRowCount(0)
            return

        # Calculer le classement précédent pour l'évolution
        previous_ranks = self._compute_previous_ranks(tournament)

        if self._1v1_mode:
            self._fill_table_1v1(tournament, previous_ranks)
        else:
            self._fill_table_standard(tournament, previous_ranks)

        # Le tableau s'adapte à l'espace disponible avec scroll si nécessaire
        if table.rowCount():
            row_h = table.rowHeight(0)
            header_h = table.horizontalHeader().height()
            frame = table.frameWidth() * 2
            min_rows = min(3, table.rowCount())
            table_min_h = header_h + row_h * min_rows + frame + 2
            table.setMinimumHeight(table_min_h)

    def set_final_standings(self, tournament, ordered_player_ids: list):
        """
        Affiche le classement final dans l'ordre bracket (appelé après la fin du tournoi).
        ordered_player_ids : IDs des joueurs dans l'ordre final (1er, 2ème, …).
        """
        previous_ranks = {}  # Pas d'évolution pour le classement final
        if self._1v1_mode:
            self._fill_table_1v1(tournament, previous_ranks, override_order=ordered_player_ids)
        else:
            self._fill_table_standard(tournament, previous_ranks, override_order=ordered_player_ids)

    def _apply_dropped_style(self, row: int):
        """Grise toutes les cellules d'une ligne (joueur abandonné)."""
        table = self.ranking_table
        drop_color = QColor("#555555")
        for col in range(table.columnCount()):
            item = table.item(row, col)
            if item:
                item.setForeground(drop_color)

    def _fill_table_1v1(self, tournament, previous_ranks, override_order=None):
        """Remplit le tableau avec les standings 1v1 (OMW%, W-D-L)."""
        table = self.ranking_table
        standings = build_standings(tournament)
        dropped_ids = {p.id for p in tournament.players if p.dropped}

        if override_order:
            entries_by_id = {e.player_id: e for e in standings}
            standings = [entries_by_id[pid] for pid in override_order if pid in entries_by_id]

        table.blockSignals(True)
        table.setRowCount(len(standings))
        self._player_ids_by_row = {}

        for row, entry in enumerate(standings):
            is_dropped = entry.player_id in dropped_ids
            current_rank = row + 1
            self._player_ids_by_row[row] = entry.player_id

            # --- Position (#) — le droppé garde son rang
            item_pos = QTableWidgetItem(str(current_rank))
            item_pos.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            table.setItem(row, 0, item_pos)

            # --- Nom joueur
            name_text = f"🚫 {entry.player_name}" if is_dropped else entry.player_name
            item_name = QTableWidgetItem(name_text)
            item_name.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            table.setItem(row, 1, item_name)

            # --- Score
            score_text = f"{entry.match_points} pts"
            item_score = QTableWidgetItem(score_text)
            item_score.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

            prev_rank = previous_ranks.get(entry.player_id)
            if is_dropped or prev_rank is None or len(tournament.rounds) <= 1:
                item_score.setForeground(QColor("#aaaaaa"))
            elif current_rank < prev_rank:
                item_score.setForeground(QColor("#3fd27d"))
            elif current_rank > prev_rank:
                item_score.setForeground(QColor("#e74c3c"))
            else:
                item_score.setForeground(QColor("#aaaaaa"))

            table.setItem(row, 2, item_score)

            # --- OMW%
            omw_text = f"{entry.omw_pct * 100:.1f}%"
            item_omw = QTableWidgetItem(omw_text)
            item_omw.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            item_omw.setForeground(QColor("#aaaaaa"))
            table.setItem(row, 3, item_omw)

            # --- GW%
            gw_text = f"{entry.gw_pct * 100:.1f}%" if entry.gw_pct > 0.0 else "—"
            item_gw = QTableWidgetItem(gw_text)
            item_gw.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            item_gw.setForeground(QColor("#aaaaaa"))
            table.setItem(row, 4, item_gw)

            # --- W-D-L
            wdl_text = f"{entry.wins}-{entry.losses}-{entry.draws}"
            item_wdl = QTableWidgetItem(wdl_text)
            item_wdl.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            item_wdl.setForeground(QColor("#aaaaaa"))
            table.setItem(row, 5, item_wdl)

            if is_dropped:
                self._apply_dropped_style(row)

        table.blockSignals(False)

    def _fill_table_standard(self, tournament, previous_ranks, override_order=None):
        """Remplit le tableau avec le classement standard (Commander/autres)."""
        table = self.ranking_table

        if override_order:
            players_by_id = {p.id: p for p in tournament.players}
            all_players = [players_by_id[pid] for pid in override_order if pid in players_by_id]
        elif self._swiss_mode:
            all_players = tournament.sort_players_swiss()
        else:
            all_players = sorted(
                tournament.players,
                key=lambda p: (-p.score, -p.robustness, p.name)
            )

        table.blockSignals(True)
        table.setRowCount(len(all_players))
        self._player_ids_by_row = {}

        for row, player in enumerate(all_players):
            is_dropped = player.dropped
            current_rank = row + 1
            self._player_ids_by_row[row] = player.id

            # --- Position (#) — le droppé garde son rang
            item_pos = QTableWidgetItem(str(current_rank))
            item_pos.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            table.setItem(row, 0, item_pos)

            # --- Nom joueur
            name_text = f"🚫 {player.name}" if is_dropped else player.name
            item_name = QTableWidgetItem(name_text)
            item_name.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            table.setItem(row, 1, item_name)

            # --- Score avec évolution colorée
            score_text = f"{player.score} pts"
            item_score = QTableWidgetItem(score_text)
            item_score.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

            item_score.setForeground(QColor("#aaaaaa"))
            table.setItem(row, 2, item_score)

            # --- Colonnes de départage Commander
            if self._swiss_mode:
                item_buchholz = QTableWidgetItem(f"{player.buchholz:.0f}")
                item_buchholz.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                item_buchholz.setForeground(QColor("#aaaaaa"))
                table.setItem(row, 3, item_buchholz)

                item_sos = QTableWidgetItem(f"{player.sos:.1f}")
                item_sos.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                item_sos.setForeground(QColor("#aaaaaa"))
                table.setItem(row, 4, item_sos)
            else:
                item_rob = QTableWidgetItem(str(player.robustness))
                item_rob.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                item_rob.setForeground(QColor("#aaaaaa"))
                table.setItem(row, 3, item_rob)

            if is_dropped:
                self._apply_dropped_style(row)

        table.blockSignals(False)

    def _compute_previous_ranks(self, tournament):
        """Calcule le classement des joueurs après le round précédent."""
        if len(tournament.rounds) < 2:
            return {}

        if self._1v1_mode:
            return self._compute_previous_ranks_1v1(tournament)

        # Commander multiplayer : scoring par position
        points_by_position = {1: 3, 2: 2, 3: 1, 4: 1}
        scores = {p.id: 0 for p in tournament.players}

        rounds_to_consider = tournament.rounds[:-1]

        for rnd in rounds_to_consider:
            if not rnd.tables:
                continue
            for tbl in rnd.tables:
                if tbl.finished:
                    for player in tbl.players:
                        position = tbl.results.get(player.id, 3)
                        scores[player.id] += points_by_position.get(position, 1)

        sorted_players = sorted(
            tournament.players,
            key=lambda p: (-scores[p.id], -p.robustness, p.name)
        )

        return {p.id: rank + 1 for rank, p in enumerate(sorted_players)}

    def _compute_previous_ranks_1v1(self, tournament):
        """Calcule le classement 1v1 après tous les rounds sauf le dernier."""
        from core.tournament import Tournament

        # Créer un tournoi temporaire avec tous les rounds sauf le dernier
        temp = Tournament(
            id=tournament.id,
            name=tournament.name,
            format=tournament.format,
            date=tournament.date,
            players=tournament.players,
            rounds=tournament.rounds[:-1],
        )

        standings = build_standings(temp)
        return {e.player_id: rank + 1 for rank, e in enumerate(standings)}

    # =================================================
    # Context menu
    # =================================================
    def _show_context_menu(self, pos):
        """Affiche le menu contextuel pour un joueur."""
        item = self.ranking_table.itemAt(pos)
        if not item:
            return

        row = item.row()
        if row not in self._player_ids_by_row:
            return

        player_id = self._player_ids_by_row[row]
        player = next((p for p in self._tournament.players if p.id == player_id), None)
        if not player:
            return

        is_regular = self._is_regular_player(player.name)

        menu = QMenu(self)

        summary_action = menu.addAction("📋 Résumé des rounds")

        menu.addSeparator()

        if is_regular:
            info_action = menu.addAction("⭐ Joueur permanent")
            info_action.setEnabled(False)
            add_action = None
        else:
            add_action = menu.addAction("➕ Ajouter aux joueurs permanents")

        menu.addSeparator()
        remove_action = menu.addAction("🚪 Retirer du tournoi")

        action = menu.exec(self.ranking_table.viewport().mapToGlobal(pos))

        if action == summary_action:
            self._show_round_summary(player_id)
        elif add_action and action == add_action:
            self._add_to_regular_players(player.name)
        elif action == remove_action:
            self.player_remove_requested.emit(player_id)

    def _show_round_summary(self, player_id: int):
        if not self._tournament:
            return
        dlg = RoundSummaryDialog(self, self._tournament, player_id)
        dlg.exec()

    def _is_regular_player(self, name: str) -> bool:
        """Vérifie si un joueur est dans la liste des joueurs permanents."""
        raw = RegularPlayerStorage.load()
        regular_players = [RegularPlayer.from_dict(d) for d in raw]
        name_lower = name.lower().strip()
        return any(p.pseudo.lower().strip() == name_lower for p in regular_players)

    def _add_to_regular_players(self, name: str):
        """Ajoute un joueur à la liste des joueurs permanents."""
        # Charger les joueurs existants
        raw = RegularPlayerStorage.load()
        regular_players = [RegularPlayer.from_dict(d) for d in raw]

        # Vérifier si le joueur existe déjà
        name_lower = name.lower().strip()
        if any(p.pseudo.lower().strip() == name_lower for p in regular_players):
            QMessageBox.information(
                self,
                "Joueur existant",
                f"« {name} » est déjà dans la liste des joueurs permanents."
            )
            return

        # Créer le nouveau joueur
        next_id = max((p.id for p in regular_players), default=0) + 1
        new_player = RegularPlayer(
            id=next_id,
            pseudo=name,
        )

        regular_players.append(new_player)

        # Sauvegarder
        RegularPlayerStorage.save([p.to_dict() for p in regular_players])

        # Notifier
        self.player_added_to_regulars.emit(name)

        QMessageBox.information(
            self,
            "Joueur ajouté",
            f"« {name} » a été ajouté aux joueurs permanents."
        )
