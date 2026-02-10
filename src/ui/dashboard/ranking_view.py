from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem,
    QHeaderView, QSizePolicy,
    QMenu, QMessageBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCursor, QColor
from ui.widgets.player_matches_popup import PlayerMatchesPopup
from core.regular_player import RegularPlayer
from storage.regular_players import RegularPlayerStorage


class DashboardRankingView(QFrame):
    # Signal émis quand un joueur est ajouté aux joueurs permanents
    player_added_to_regulars = Signal(str)  # pseudo du joueur

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("DashboardCard")

        self._tournament = None
        self._player_results = {}  # player_id -> list of round results
        self._previous_ranks = {}  # player_id -> rank at previous round
        self._swiss_mode = False

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
        table.setMouseTracking(True)

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

        # --- Hover events ---
        table.cellEntered.connect(self._on_cell_hover)

        # --- Context menu ---
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(self._show_context_menu)

        layout.addWidget(table, 1)

        self.ranking_table = table
        self.ranking_viewport = table.viewport()

        self.popup = PlayerMatchesPopup(self)
        self.popup.hide()

        self._current_hover_row = -1
        self._player_ids_by_row = {}

    # =================================================
    # Public API
    # =================================================
    def set_swiss_mode(self, enabled: bool):
        """Configure l'affichage pour le mode Swiss."""
        self._swiss_mode = enabled
        table = self.ranking_table

        if enabled:
            table.setColumnCount(5)
            table.setHorizontalHeaderLabels(["#", "Joueur", "Score", "Buchholz", "SOS"])

            header = table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        else:
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["#", "Joueur", "Score"])

            header = table.horizontalHeader()
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

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

        # Calculer les résultats par joueur
        self._compute_player_results(tournament)

        # Calculer le classement précédent pour l'évolution
        previous_ranks = self._compute_previous_ranks(tournament)

        # Trier selon le mode (Swiss ou standard)
        if self._swiss_mode:
            players = tournament.sort_players_swiss()
        else:
            players = sorted(
                tournament.players,
                key=lambda p: (-p.score, -p.robustness, p.name)
            )

        table.setRowCount(len(players))
        self._player_ids_by_row = {}

        for row, player in enumerate(players):
            current_rank = row + 1
            self._player_ids_by_row[row] = player.id

            # --- Position (#)
            item_pos = QTableWidgetItem(str(current_rank))
            item_pos.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            table.setItem(row, 0, item_pos)

            # --- Nom joueur (CENTRÉ)
            item_name = QTableWidgetItem(player.name)
            item_name.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            table.setItem(row, 1, item_name)

            # --- Score avec évolution colorée
            score_text = f"{player.score} pts"
            item_score = QTableWidgetItem(score_text)
            item_score.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)

            # Déterminer la couleur selon l'évolution
            prev_rank = previous_ranks.get(player.id)
            if prev_rank is None or len(tournament.rounds) <= 1:
                # Pas de round précédent, gris
                item_score.setForeground(QColor("#aaaaaa"))
            elif current_rank < prev_rank:
                # Gagné des places, vert
                item_score.setForeground(QColor("#3fd27d"))
            elif current_rank > prev_rank:
                # Perdu des places, rouge
                item_score.setForeground(QColor("#e74c3c"))
            else:
                # Pas bougé, gris
                item_score.setForeground(QColor("#aaaaaa"))

            table.setItem(row, 2, item_score)

            # --- Colonnes Swiss (Buchholz et SOS)
            if self._swiss_mode:
                item_buchholz = QTableWidgetItem(f"{player.buchholz:.0f}")
                item_buchholz.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                item_buchholz.setForeground(QColor("#aaaaaa"))
                table.setItem(row, 3, item_buchholz)

                item_sos = QTableWidgetItem(f"{player.sos:.1f}")
                item_sos.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
                item_sos.setForeground(QColor("#aaaaaa"))
                table.setItem(row, 4, item_sos)

        # =====================
        # 🔑 Le tableau s'adapte à l'espace disponible avec scroll si nécessaire
        # =====================
        if table.rowCount():
            row_h = table.rowHeight(0)
            header_h = table.horizontalHeader().height()
            frame = table.frameWidth() * 2

            # Hauteur minimale pour afficher au moins 3 lignes
            min_rows = min(3, table.rowCount())
            table_min_h = header_h + row_h * min_rows + frame + 2
            table.setMinimumHeight(table_min_h)

    # =================================================
    # Compute player results per round
    # =================================================
    def _compute_player_results(self, tournament):
        """Calcule les résultats de chaque joueur pour chaque round."""
        self._player_results = {p.id: [] for p in tournament.players}

        position_labels = {1: "🥇 1er", 2: "🥈 2ème", 3: "🥉 3ème", 4: "4ème"}
        points_by_position = {1: 3, 2: 2, 3: 1, 4: 1}

        for rnd in tournament.rounds:
            if not rnd.tables:
                continue
            for tbl in rnd.tables:
                for player in tbl.players:
                    position = tbl.results.get(player.id)
                    if position is not None:
                        self._player_results[player.id].append({
                            "round": rnd.number,
                            "table": tbl.number,
                            "position": position_labels.get(position, f"{position}ème"),
                            "points": points_by_position.get(position, 1),
                        })

    def _compute_previous_ranks(self, tournament):
        """Calcule le classement des joueurs après le round précédent."""
        if len(tournament.rounds) < 2:
            return {}

        # Calculer les scores après tous les rounds sauf le dernier
        points_by_position = {1: 3, 2: 2, 3: 1, 4: 1}
        scores = {p.id: 0 for p in tournament.players}

        # Ne prendre que les rounds terminés sauf le dernier
        rounds_to_consider = tournament.rounds[:-1]

        for rnd in rounds_to_consider:
            if not rnd.tables:
                continue
            for tbl in rnd.tables:
                if tbl.finished:
                    for player in tbl.players:
                        position = tbl.results.get(player.id, 3)
                        scores[player.id] += points_by_position.get(position, 1)

        # Trier pour obtenir le classement (on ne peut pas utiliser la robustesse historique ici)
        sorted_players = sorted(
            tournament.players,
            key=lambda p: (-scores[p.id], -p.robustness, p.name)
        )

        return {p.id: rank + 1 for rank, p in enumerate(sorted_players)}

    # =================================================
    # Hover handling
    # =================================================
    def _on_cell_hover(self, row, col):
        if row == self._current_hover_row:
            return

        self._current_hover_row = row

        if row < 0 or row not in self._player_ids_by_row:
            self.popup.hide()
            return

        player_id = self._player_ids_by_row[row]
        results = self._player_results.get(player_id, [])

        if not results:
            self.popup.hide()
            return

        # Trouver le joueur
        player = None
        for p in self._tournament.players:
            if p.id == player_id:
                player = p
                break

        if not player:
            self.popup.hide()
            return

        self.popup.set_player(player.name, results, player.robustness)

        # Positionner le popup près du curseur
        cursor_pos = QCursor.pos()
        self.popup.move(cursor_pos.x() + 15, cursor_pos.y() + 10)
        self.popup.show()

    def leaveEvent(self, event):
        """Cache le popup quand la souris quitte le widget."""
        super().leaveEvent(event)
        self.popup.hide()
        self._current_hover_row = -1

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

        # Vérifier si le joueur est déjà dans les joueurs permanents
        is_regular = self._is_regular_player(player.name)

        menu = QMenu(self)

        if is_regular:
            info_action = menu.addAction("⭐ Joueur permanent")
            info_action.setEnabled(False)
        else:
            add_action = menu.addAction("➕ Ajouter aux joueurs permanents")

        action = menu.exec(self.ranking_table.viewport().mapToGlobal(pos))

        if not is_regular and action:
            self._add_to_regular_players(player.name)

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
