from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout,
    QLabel, QWidget, QMenu
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

        self._round: Round | None = None

        # === ROOT LAYOUT ===
        root_layout = QVBoxLayout(self)
        root_layout.setSpacing(12)

        # === TITLE ===
        title = QLabel("🎲 Tables en cours")
        title.setObjectName("DashboardSectionTitle")
        root_layout.addWidget(title)

        # === SCROLL AREA ===
        self.scroll = HorizontalScrollArea()
        self.scroll.setObjectName("TablesScrollArea")
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setMinimumHeight(170)

        # === CONTAINER ===
        self.container = QWidget()
        self.container.setObjectName("TablesScrollContent")

        # === HORIZONTAL LAYOUT ===
        self.h_layout = QHBoxLayout(self.container)
        self.h_layout.setSpacing(16)
        self.h_layout.setContentsMargins(16, 0, 16, 0)
        self.h_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        self.scroll.setWidget(self.container)
        root_layout.addWidget(self.scroll)

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

        if not round_:
            return

        # Création des cartes
        for table in round_.tables:
            self.h_layout.addWidget(self._table_card(table))

        # Stretch TOUJOURS en dernier
        self.h_layout.addStretch()

    # ======================================================
    # Table card
    # ======================================================
    def _table_card(self, table: Table) -> QFrame:
        card = QFrame()
        card.setObjectName("TableCard")
        card.setFixedSize(220, 150)

        card.setContextMenuPolicy(Qt.CustomContextMenu)
        card.customContextMenuRequested.connect(
            lambda pos, t=table: self._show_table_context_menu(card, pos, t)
        )

        layout = QVBoxLayout(card)
        layout.setSpacing(6)

        lbl_id = QLabel(f"Table {table.number}")
        lbl_id.setObjectName("TableCardTitle")

        players_text = " vs ".join(player.name for player in table.players)
        lbl_players = QLabel(players_text)
        lbl_players.setObjectName("TableCardPlayers")
        lbl_players.setWordWrap(True)
        lbl_players.setMaximumHeight(40)

        layout.addWidget(lbl_id)
        layout.addWidget(lbl_players)

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
