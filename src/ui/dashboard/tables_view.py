from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout,
    QLabel, QWidget, QMenu, QSizePolicy
)
from PySide6.QtCore import Qt, Signal

from core.round import Round
from core.table import Table
from ui.widgets.horizontal_scroll_area import HorizontalScrollArea


class DashboardTablesView(QFrame):

    edit_results_requested = Signal(Table)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("DashboardCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._round: Round | None = None

        # === ROOT LAYOUT ===
        root_layout = QVBoxLayout(self)
        root_layout.setSpacing(12)

        # === TITLE ===
        self.title = QLabel("🎲 Tables en cours")
        self.title.setObjectName("DashboardSectionTitle")
        root_layout.addWidget(self.title)

        # === SCROLL AREA ===
        self.scroll = HorizontalScrollArea()
        self.scroll.setObjectName("TablesScrollArea")
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # === CONTAINER ===
        self.container = QWidget()
        self.container.setObjectName("TablesScrollContent")
        self.container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # === HORIZONTAL LAYOUT ===
        self.h_layout = QHBoxLayout(self.container)
        self.h_layout.setSpacing(16)
        self.h_layout.setContentsMargins(16, 4, 16, 4)

        self.scroll.setWidget(self.container)
        root_layout.addWidget(self.scroll, 1)

    # ======================================================
    # Public API
    # ======================================================
    def set_round(self, round_: Round):
        self._round = round_

        # Nettoyage du layout
        while self.h_layout.count():
            item = self.h_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not round_ or not round_.tables:
            return

        # Création des cartes
        for table in round_.tables:
            card = self._table_card(table)
            self.h_layout.addWidget(card)

        # Stretch TOUJOURS en dernier
        self.h_layout.addStretch()

    # ======================================================
    # Table card
    # ======================================================
    def _table_card(self, table: Table) -> QFrame:
        card = QFrame()
        card.setObjectName("TableCard")
        card.setMinimumWidth(200)
        card.setMaximumWidth(280)
        card.setMinimumHeight(80)
        card.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        layout = QVBoxLayout(card)
        layout.setSpacing(6)

        # Cas spécial: table BYE (1 seul joueur)
        if len(table.players) == 1:
            lbl_id = QLabel(f"Table {table.number} - BYE")
            lbl_id.setObjectName("TableCardTitle")

            player = table.players[0]
            lbl_players = QLabel(player.name)
            lbl_players.setObjectName("TableCardPlayers")
            lbl_players.setWordWrap(True)
            lbl_players.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

            layout.addWidget(lbl_id)
            layout.addWidget(lbl_players, 1)

            status = QLabel("⚖️ Victoire automatique (+3 pts)")
            status.setObjectName("TableCardFinished")
            layout.addWidget(status)

            card.setProperty("status", "bye")
            return card

        # Table normale
        card.setContextMenuPolicy(Qt.CustomContextMenu)
        card.customContextMenuRequested.connect(
            lambda pos, t=table: self._show_table_context_menu(card, pos, t)
        )

        lbl_id = QLabel(f"Table {table.number}")
        lbl_id.setObjectName("TableCardTitle")

        players_text = " vs ".join(player.name for player in table.players)
        lbl_players = QLabel(players_text)
        lbl_players.setObjectName("TableCardPlayers")
        lbl_players.setWordWrap(True)
        lbl_players.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)

        layout.addWidget(lbl_id)
        layout.addWidget(lbl_players, 1)

        if table.finished:
            status = QLabel("✔ Terminée")
            status.setObjectName("TableCardFinished")

            winner = None

            # Cherche le joueur avec position 1 dans les résultats
            for player in table.players:
                if table.results.get(player.id) == 1:
                    winner = player
                    break

            if winner:
                winner_lbl = QLabel(f"Gagnant : {winner.name}")
                winner_lbl.setObjectName("TableCardWinner")
                layout.addWidget(winner_lbl)

            card.setProperty("status", "finished")
        else:
            status = QLabel("⏳ En cours")
            status.setObjectName("TableCardRunning")
            card.setProperty("status", "running")

        layout.addWidget(status)

        return card

    def _show_table_context_menu(self, card: QFrame, pos, table: Table):
        menu = QMenu(card)

        edit_action = menu.addAction("✏️ Définir les résultats")

        # (prévu pour plus tard)
        menu.addSeparator()
        close_action = menu.addAction("❌ Annuler")

        action = menu.exec(card.mapToGlobal(pos))

        if action == edit_action:
            self.edit_results_requested.emit(table)
