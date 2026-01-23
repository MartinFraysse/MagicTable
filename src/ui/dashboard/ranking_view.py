from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem,
    QHeaderView, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QCursor
from ui.widgets.player_matches_popup import PlayerMatchesPopup

import random


class DashboardRankingView(QFrame):
    VISIBLE_ROWS = 8

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("DashboardCard")

        self.player_matches = {}
        self._last_popup_pos = None

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
        table.setHorizontalHeaderLabels(["#", "Joueur", "Évolution"])
        table.verticalHeader().setVisible(False)

        # --- Comportement ---
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setFocusPolicy(Qt.NoFocus)

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

        layout.addWidget(table)
        layout.addStretch(1)

        self.ranking_table = table
        self.ranking_viewport = table.viewport()

        self.popup = PlayerMatchesPopup(self)
        self.popup.hide()

    # =================================================
    # Public API
    # =================================================
    def set_tournament(self, tournament):
        table = self.ranking_table

        if not tournament:
            table.setRowCount(0)
            return

        players = tournament.players[:]
        random.shuffle(players)

        table.setRowCount(len(players))

        for row, player in enumerate(players):
            # --- Position (#)
            item_pos = QTableWidgetItem(str(row + 1))
            item_pos.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            table.setItem(row, 0, item_pos)

            # --- Nom joueur (CENTRÉ)
            item_name = QTableWidgetItem(player.name)
            item_name.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            table.setItem(row, 1, item_name)

            # --- Évolution
            item_delta = QTableWidgetItem("— 0")
            item_delta.setTextAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
            item_delta.setForeground(Qt.lightGray)
            table.setItem(row, 2, item_delta)

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
