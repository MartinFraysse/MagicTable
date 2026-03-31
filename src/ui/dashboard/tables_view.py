from PySide6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout,
    QLabel, QWidget, QMenu, QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QMouseEvent

from core.round import Round
from core.table import Table
from core.bracket import BracketMatch
from ui.widgets.horizontal_scroll_area import HorizontalScrollArea


class _ClickableCard(QFrame):
    """Carte de table cliquable (double-clic pour éditer les résultats)."""
    double_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit()
        super().mouseDoubleClickEvent(event)


class DashboardTablesView(QFrame):

    edit_results_requested = Signal(Table)
    edit_bracket_result_requested = Signal(object)  # BracketMatch

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
        card = _ClickableCard()
        card.setObjectName("TableCard")
        card.setMinimumWidth(200)
        card.setMaximumWidth(280)
        card.setMinimumHeight(80)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(card)
        layout.setSpacing(6)

        # Cas spécial: table BYE (1 seul joueur)
        if len(table.players) == 1:
            lbl_id = QLabel(f"Table {table.number} - BYE")
            lbl_id.setObjectName("TableCardTitle")
            lbl_id.setAttribute(Qt.WA_TransparentForMouseEvents)

            player = table.players[0]
            lbl_players = QLabel(player.name)
            lbl_players.setObjectName("TableCardPlayers")
            lbl_players.setWordWrap(True)
            lbl_players.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
            lbl_players.setAttribute(Qt.WA_TransparentForMouseEvents)

            layout.addWidget(lbl_id)
            layout.addWidget(lbl_players, 1)

            status = QLabel("⚖️ Victoire automatique")
            status.setObjectName("TableCardFinished")
            status.setAttribute(Qt.WA_TransparentForMouseEvents)
            layout.addWidget(status)

            card.setProperty("status", "bye")
            return card

        # Table normale : double-clic et menu contextuel
        card.double_clicked.connect(
            lambda t=table: self.edit_results_requested.emit(t)
        )
        card.setContextMenuPolicy(Qt.CustomContextMenu)
        card.customContextMenuRequested.connect(
            lambda pos, t=table: self._show_table_context_menu(card, pos, t)
        )

        lbl_id = QLabel(f"Table {table.number}")
        lbl_id.setObjectName("TableCardTitle")
        lbl_id.setAttribute(Qt.WA_TransparentForMouseEvents)

        players_text = " vs ".join(player.name for player in table.players)
        lbl_players = QLabel(players_text)
        lbl_players.setObjectName("TableCardPlayers")
        lbl_players.setWordWrap(True)
        lbl_players.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        lbl_players.setAttribute(Qt.WA_TransparentForMouseEvents)

        layout.addWidget(lbl_id)
        layout.addWidget(lbl_players, 1)

        if table.finished:
            status = QLabel("✔ Terminée")
            status.setObjectName("TableCardFinished")

            winner = None
            is_draw = False

            # Cherche le joueur avec position 1
            for player in table.players:
                pos = table.results.get(player.id)
                if pos == 1:
                    winner = player
                    break

            # Détection nul : deux joueurs avec même position (pas de pos 1)
            if winner is None and len(table.players) == 2:
                pos_values = [table.results.get(p.id) for p in table.players]
                if len(set(pos_values)) == 1:
                    is_draw = True

            if is_draw:
                g1 = table.game_scores.get(table.players[0].id)
                g2 = table.game_scores.get(table.players[1].id)
                if g1 is not None and g2 is not None:
                    draw_text = f"⚖️ Nul ({g1}-{g2})"
                else:
                    draw_text = "⚖️ Match nul"
                draw_lbl = QLabel(draw_text)
                draw_lbl.setObjectName("TableCardWinner")
                draw_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
                layout.addWidget(draw_lbl)
            elif winner:
                loser_games = None
                winner_games = table.game_scores.get(winner.id)
                if winner_games is not None:
                    loser_games = next(
                        (table.game_scores.get(p.id) for p in table.players if p.id != winner.id),
                        None
                    )
                if winner_games is not None and loser_games is not None:
                    score_str = f" ({winner_games}-{loser_games})"
                else:
                    score_str = ""
                winner_lbl = QLabel(f"Gagnant : {winner.name}{score_str}")
                winner_lbl.setObjectName("TableCardWinner")
                winner_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
                layout.addWidget(winner_lbl)

            card.setProperty("status", "finished")
        else:
            status = QLabel("⏳ En cours")
            status.setObjectName("TableCardRunning")
            card.setProperty("status", "running")

        status.setAttribute(Qt.WA_TransparentForMouseEvents)
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

    # ======================================================
    # Bracket display
    # ======================================================
    def set_bracket_round(self, matches: list, players_by_id: dict):
        """Affiche les matches du round de bracket actif."""
        while self.h_layout.count():
            item = self.h_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not matches:
            self.h_layout.addStretch()
            return

        for match in matches:
            card = self._bracket_match_card(match, players_by_id)
            self.h_layout.addWidget(card)

        self.h_layout.addStretch()

    def _bracket_match_card(self, match: BracketMatch, players_by_id: dict) -> QFrame:
        card = _ClickableCard()
        card.setObjectName("TableCard")
        card.setMinimumWidth(200)
        card.setMaximumWidth(280)
        card.setMinimumHeight(80)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(card)
        layout.setSpacing(6)

        pos_labels = ["Match A", "Match B", "Match C", "Match D"]
        pos_text = pos_labels[match.position] if match.position < len(pos_labels) else f"Match {match.position + 1}"
        lbl_id = QLabel(pos_text)
        lbl_id.setObjectName("TableCardTitle")
        lbl_id.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(lbl_id)

        p1 = players_by_id.get(match.player1_id)
        p2 = players_by_id.get(match.player2_id)

        if p1 is None or p2 is None:
            waiting_lbl = QLabel("⏳ En attente...")
            waiting_lbl.setObjectName("TableCardPlayers")
            waiting_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
            layout.addWidget(waiting_lbl, 1)
            card.setProperty("status", "waiting")
            return card

        players_text = f"{p1.name} vs {p2.name}"
        lbl_players = QLabel(players_text)
        lbl_players.setObjectName("TableCardPlayers")
        lbl_players.setWordWrap(True)
        lbl_players.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        lbl_players.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(lbl_players, 1)

        if match.finished:
            winner = players_by_id.get(match.winner_id)
            if winner:
                winner_lbl = QLabel(f"Gagnant : {winner.name}")
                winner_lbl.setObjectName("TableCardWinner")
                winner_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
                layout.addWidget(winner_lbl)

            status_lbl = QLabel("✔ Terminée")
            status_lbl.setObjectName("TableCardFinished")
            status_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
            layout.addWidget(status_lbl)
            card.setProperty("status", "finished")
        else:
            card.double_clicked.connect(
                lambda m=match: self.edit_bracket_result_requested.emit(m)
            )
            card.setContextMenuPolicy(Qt.CustomContextMenu)
            card.customContextMenuRequested.connect(
                lambda pos, m=match: self._show_bracket_context_menu(card, pos, m)
            )

            status_lbl = QLabel("⏳ En cours")
            status_lbl.setObjectName("TableCardRunning")
            status_lbl.setAttribute(Qt.WA_TransparentForMouseEvents)
            layout.addWidget(status_lbl)
            card.setProperty("status", "running")

        return card

    def _show_bracket_context_menu(self, card: QFrame, pos, match: BracketMatch):
        menu = QMenu(card)
        edit_action = menu.addAction("✏️ Définir le vainqueur")
        menu.addSeparator()
        menu.addAction("❌ Annuler")
        action = menu.exec(card.mapToGlobal(pos))
        if action == edit_action:
            self.edit_bracket_result_requested.emit(match)
