from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem,
    QHeaderView, QSizePolicy
)
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QCursor, QColor
from ui.widgets.player_matches_popup import PlayerMatchesPopup


class DashboardRankingView(QFrame):
    VISIBLE_ROWS = 8

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("DashboardCard")

        self._tournament = None
        self._player_results = {}  # player_id -> list of round results
        self._previous_ranks = {}  # player_id -> rank at previous round

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
        table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
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
        table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Maximum)

        # --- Hover events ---
        table.cellEntered.connect(self._on_cell_hover)

        layout.addWidget(table)
        layout.addStretch(1)

        self.ranking_table = table
        self.ranking_viewport = table.viewport()

        self.popup = PlayerMatchesPopup(self)
        self.popup.hide()

        self._current_hover_row = -1
        self._player_ids_by_row = {}

    # =================================================
    # Public API
    # =================================================
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

        # Trier les joueurs par score décroissant, puis robustesse, puis par nom
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

        # =====================
        # 🔑 Hauteur exacte pour 8 lignes
        # =====================
        if table.rowCount():
            row_h = table.rowHeight(0)
            header_h = table.horizontalHeader().height()
            frame = table.frameWidth() * 2

            table_min_h = (
                header_h
                + row_h * self.VISIBLE_ROWS
                + frame
                + 2
            )

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
