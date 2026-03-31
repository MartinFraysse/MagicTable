from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from core.tournament import Tournament
from core.round import Round
from core.table import Table


_POINTS_COMMANDER = {1: 3, 2: 2, 3: 1, 4: 1}
_POSITIONS_FR     = {1: "1er", 2: "2ème", 3: "3ème", 4: "4ème"}

# Couleurs résultats (lisibles dark + light)
_COL_WIN   = "#28c47a"
_COL_DRAW  = "#c8960c"
_COL_LOSS  = "#d94848"
_COL_BYE   = "#28c47a"
_COL_GOLD  = "#c89020"
_COL_BLUE  = "#5888c8"
_COL_GRAY  = "#888888"
_COL_MUTED = "#7a9f92"


class RoundSummaryDialog(QDialog):
    """Affiche le parcours d'un joueur round par round, format compact."""

    ROW_H    = 30
    HEADER_H = 28
    MAX_ROWS = 12

    def __init__(self, parent, tournament: Tournament, player_id: int):
        super().__init__(parent)

        self._tournament  = tournament
        self._player_id   = player_id
        self._is_commander = "Commander" in tournament.format

        player = next((p for p in tournament.players if p.id == player_id), None)
        self._player_name = player.name if player else "Joueur"

        self.setWindowTitle(f"Parcours — {self._player_name}")
        self.setObjectName("RoundSummaryDialog")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setModal(True)
        self.setFixedWidth(480 if self._is_commander else 400)

        self._build_ui()

        n       = len(tournament.rounds)
        table_h = min(self.HEADER_H + n * self.ROW_H,
                      self.HEADER_H + self.MAX_ROWS * self.ROW_H)
        self.setFixedHeight(table_h + 120)  # 120 = marges + titre + méta + espacements + footer

    # ------------------------------------------------------------------
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(16, 16, 16, 14)

        # Titre
        title = QLabel(f"🗺  {self._player_name}")
        title.setObjectName("DetailTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        meta = QLabel(f"{self._tournament.name}  •  {self._tournament.format}")
        meta.setObjectName("DetailMeta")
        meta.setAlignment(Qt.AlignCenter)
        layout.addWidget(meta)

        layout.addSpacing(4)

        # Tableau
        if self._is_commander:
            cols = ["Rd", "Table", "Position", "Adversaires"]
        else:
            cols = ["Rd", "Table", "Résultat", "Adversaire"]

        self._tbl = QTableWidget()
        self._tbl.setObjectName("RankingTable")
        self._tbl.setColumnCount(len(cols))
        self._tbl.setHorizontalHeaderLabels(cols)
        self._tbl.setRowCount(len(self._tournament.rounds))
        self._tbl.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setShowGrid(False)
        self._tbl.setAlternatingRowColors(True)
        self._tbl.verticalHeader().setDefaultSectionSize(self.ROW_H)

        hdr = self._tbl.horizontalHeader()
        hdr.setHighlightSections(False)
        hdr.setSectionResizeMode(0, QHeaderView.Fixed)
        hdr.setSectionResizeMode(1, QHeaderView.Fixed)
        hdr.setSectionResizeMode(2, QHeaderView.Fixed)
        hdr.setSectionResizeMode(3, QHeaderView.Stretch)
        self._tbl.setColumnWidth(0, 32)
        self._tbl.setColumnWidth(1, 56)
        self._tbl.setColumnWidth(2, 130 if self._is_commander else 120)

        for row, rnd in enumerate(self._tournament.rounds):
            self._fill_row(row, rnd, self._find_table(rnd))

        n       = len(self._tournament.rounds)
        exact_h = self.HEADER_H + n * self.ROW_H
        max_h   = self.HEADER_H + self.MAX_ROWS * self.ROW_H
        self._tbl.setFixedHeight(min(exact_h, max_h))
        self._tbl.setVerticalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff if n <= self.MAX_ROWS else Qt.ScrollBarAsNeeded
        )
        layout.addWidget(self._tbl)

        # Footer
        footer = QHBoxLayout()
        footer.addStretch()
        close_btn = QPushButton("Fermer")
        close_btn.setObjectName("CancelButton")
        close_btn.setMinimumHeight(32)
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)
        layout.addLayout(footer)

    # ------------------------------------------------------------------
    def _fill_row(self, row: int, rnd: Round, tbl: Table | None):
        self._cell(row, 0, str(rnd.number), Qt.AlignCenter)

        if not tbl:
            self._cell(row, 1, "—",      Qt.AlignCenter)
            self._cell(row, 2, "Absent", Qt.AlignCenter, _COL_MUTED)
            self._cell(row, 3, "—",      Qt.AlignLeft | Qt.AlignVCenter)
            return

        is_bye = len(tbl.players) == 1
        if is_bye:
            self._cell(row, 1, "BYE",    Qt.AlignCenter, _COL_BYE)
            self._cell(row, 2, "+3 pts", Qt.AlignCenter, _COL_BYE)
            self._cell(row, 3, "—",      Qt.AlignLeft | Qt.AlignVCenter)
            return

        self._cell(row, 1, f"T{tbl.number}", Qt.AlignCenter)

        if not tbl.finished:
            self._cell(row, 2, "En cours…", Qt.AlignCenter, _COL_MUTED)
            self._cell(row, 3, "—",         Qt.AlignLeft | Qt.AlignVCenter)
            return

        if self._is_commander:
            self._fill_commander(row, tbl)
        else:
            self._fill_1v1(row, tbl)

    def _fill_commander(self, row: int, tbl: Table):
        pos  = tbl.results.get(self._player_id)
        pts  = _POINTS_COMMANDER.get(pos, 0)
        col  = {1: _COL_GOLD, 2: _COL_BLUE}.get(pos, _COL_GRAY)
        text = f"{_POSITIONS_FR.get(pos, '—')}  +{pts} pts"
        self._cell(row, 2, text, Qt.AlignCenter, col)

        opps  = [p for p in tbl.players if p.id != self._player_id]
        names = "  •  ".join(p.name for p in opps) if opps else "—"
        self._cell(row, 3, names, Qt.AlignLeft | Qt.AlignVCenter)

    def _fill_1v1(self, row: int, tbl: Table):
        my_pos   = tbl.results.get(self._player_id)
        opps     = [p for p in tbl.players if p.id != self._player_id]
        opp      = opps[0] if opps else None
        opp_pos  = tbl.results.get(opp.id) if opp else None

        is_win  = (my_pos == 1)
        is_draw = (my_pos == 2 and opp_pos == 2)

        my_g  = tbl.game_scores.get(self._player_id)
        opp_g = tbl.game_scores.get(opp.id) if opp else None
        bo3   = f" {my_g}‑{opp_g}" if (my_g is not None and opp_g is not None) else ""

        if is_win:
            label, pts, col = "Victoire", 3, _COL_WIN
        elif is_draw:
            label, pts, col = "Nul",      1, _COL_DRAW
        else:
            label, pts, col = "Défaite",  0, _COL_LOSS

        self._cell(row, 2, f"{label}{bo3}  +{pts} pts", Qt.AlignCenter, col)
        self._cell(row, 3, opp.name if opp else "—", Qt.AlignLeft | Qt.AlignVCenter)

    # ------------------------------------------------------------------
    def _cell(self, row: int, col: int, text: str,
              align=Qt.AlignCenter, color: str | None = None):
        item = QTableWidgetItem(text)
        item.setTextAlignment(align)
        if color:
            item.setForeground(QColor(color))
        self._tbl.setItem(row, col, item)

    def _find_table(self, rnd: Round) -> Table | None:
        for t in (rnd.tables or []):
            if any(p.id == self._player_id for p in t.players):
                return t
        return None
