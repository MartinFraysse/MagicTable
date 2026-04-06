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
from core.bracket import BracketRoundName


_POINTS_COMMANDER = {1: 3, 2: 2, 3: 1, 4: 1}
_POSITIONS_FR     = {1: "1er", 2: "2ème", 3: "3ème", 4: "4ème"}

_BRACKET_ROUND_LABEL = {
    BracketRoundName.QUART: "Quart",
    BracketRoundName.DEMI:  "Demi",
    BracketRoundName.FINAL: "Finale",
}
_BRACKET_ROUND_ORDER = {
    BracketRoundName.QUART: 0,
    BracketRoundName.DEMI:  1,
    BracketRoundName.FINAL: 2,
}

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

        self._build_ui()

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
            cols = ["Rd", "Table", "Résultat", "Adversaires"]
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
        self._tbl.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        hdr = self._tbl.horizontalHeader()
        hdr.setHighlightSections(False)
        hdr.setSectionResizeMode(0, QHeaderView.Fixed)
        hdr.setSectionResizeMode(1, QHeaderView.Fixed)
        hdr.setSectionResizeMode(2, QHeaderView.Fixed)
        hdr.setSectionResizeMode(3, QHeaderView.Fixed)
        self._tbl.setColumnWidth(0, 32)
        self._tbl.setColumnWidth(1, 48)
        self._tbl.setColumnWidth(2, 90 if self._is_commander else 72)
        self._tbl.setColumnWidth(3, 160 if self._is_commander else 150)

        for row, rnd in enumerate(self._tournament.rounds):
            self._fill_row(row, rnd, self._find_table(rnd))

        # ── Lignes bracket ──────────────────────────────────────────
        bracket_matches = self._find_bracket_matches()
        swiss_count = len(self._tournament.rounds)
        extra_rows = 0

        if bracket_matches:
            extra_rows = 1 + len(bracket_matches)  # 1 séparateur + N matchs
            self._tbl.setRowCount(swiss_count + extra_rows)

            sep = QTableWidgetItem("  🏆  Phase finale")
            sep.setForeground(QColor(_COL_GOLD))
            sep.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            self._tbl.setSpan(swiss_count, 0, 1, self._tbl.columnCount())
            self._tbl.setItem(swiss_count, 0, sep)

            for i, match in enumerate(bracket_matches):
                self._fill_bracket_row(swiss_count + 1 + i, match)

        # ── Largeur col 3 : Qt mesure le contenu réel ────────────────
        self._tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._tbl.resizeColumnToContents(3)
        col3_w = self._tbl.columnWidth(3) + 16   # +16 px de marge de sécurité
        self._tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.Fixed)
        self._tbl.setColumnWidth(3, col3_w)

        # Largeur fenêtre : marges layout (32) + col0-3 + bordures table (16)
        col2_w = 90 if self._is_commander else 72
        self.setFixedWidth(32 + 32 + 48 + col2_w + col3_w + 16)

        n       = swiss_count + extra_rows
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

        # Hauteur : table + éléments fixes (marges 30 + titre 22 + meta 18 + spacing(4) + 4×spacing(8) + footer 36)
        self.setFixedHeight(self._tbl.height() + 158)

    # ------------------------------------------------------------------
    def _fill_row(self, row: int, rnd: Round, tbl: Table | None):
        self._cell(row, 0, str(rnd.number), Qt.AlignCenter)

        if not tbl:
            self._cell(row, 1, "—",      Qt.AlignCenter)
            self._cell(row, 2, "Absent", Qt.AlignCenter, _COL_MUTED)
            self._cell(row, 3, "—",      Qt.AlignCenter)
            return

        is_bye = len(tbl.players) == 1
        if is_bye:
            self._cell(row, 1, "BYE",    Qt.AlignCenter, _COL_BYE)
            self._cell(row, 2, "+3 pts", Qt.AlignCenter, _COL_BYE)
            self._cell(row, 3, "—",      Qt.AlignCenter)
            return

        self._cell(row, 1, f"T{tbl.number}", Qt.AlignCenter)

        if not tbl.finished:
            self._cell(row, 2, "En cours…", Qt.AlignCenter, _COL_MUTED)
            self._cell(row, 3, "—",         Qt.AlignCenter)
            return

        if self._is_commander:
            self._fill_commander(row, tbl)
        else:
            self._fill_1v1(row, tbl)

    def _fill_commander(self, row: int, tbl: Table):
        pos  = tbl.results.get(self._player_id)
        opps = [p for p in tbl.players if p.id != self._player_id]

        is_multi = len(tbl.players) > 2
        if is_multi:
            if pos == 1:
                score_text, col = "1er",    _COL_GOLD
            elif pos == 2:
                score_text, col = "2ème",   _COL_BLUE
            else:
                score_text, col = "3/4ème", _COL_GRAY
        else:
            # 2 joueurs : score BO3 si disponible
            my_g  = tbl.game_scores.get(self._player_id) if tbl.game_scores else None
            opp   = opps[0] if opps else None
            opp_g = tbl.game_scores.get(opp.id) if (opp and tbl.game_scores) else None
            if my_g is not None and opp_g is not None:
                score_text = f"{my_g}‑{opp_g}"
                col = _COL_WIN if my_g > opp_g else (_COL_DRAW if my_g == opp_g else _COL_LOSS)
            else:
                score_text, col = "—", _COL_GRAY

        self._cell(row, 2, score_text, Qt.AlignCenter, col)
        names = "  •  ".join(p.name for p in opps) if opps else "—"
        self._cell(row, 3, names, Qt.AlignCenter)

    def _fill_1v1(self, row: int, tbl: Table):
        my_pos   = tbl.results.get(self._player_id)
        opps     = [p for p in tbl.players if p.id != self._player_id]
        opp      = opps[0] if opps else None
        opp_pos  = tbl.results.get(opp.id) if opp else None

        is_win  = (my_pos == 1)
        is_draw = (my_pos == 2 and opp_pos == 2)

        my_g  = tbl.game_scores.get(self._player_id)
        opp_g = tbl.game_scores.get(opp.id) if opp else None

        if is_win:
            col = _COL_WIN
        elif is_draw:
            col = _COL_DRAW
        else:
            col = _COL_LOSS

        if my_g is not None and opp_g is not None:
            score_text = f"{my_g}‑{opp_g}"
        elif is_win:
            score_text = "Victoire"
        elif is_draw:
            score_text = "Nul"
        else:
            score_text = "Défaite"

        self._cell(row, 2, score_text, Qt.AlignCenter, col)
        self._cell(row, 3, opp.name if opp else "—", Qt.AlignCenter)

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

    # ------------------------------------------------------------------
    def _find_bracket_matches(self) -> list:
        """Retourne les matchs de bracket impliquant ce joueur, triés par round."""
        bracket = self._tournament.bracket
        if not bracket:
            return []
        matches = [
            m for m in bracket.matches
            if self._player_id in (m.player1_id, m.player2_id)
        ]
        matches.sort(key=lambda m: _BRACKET_ROUND_ORDER.get(m.round_name, 99))
        return matches

    def _fill_bracket_row(self, row: int, match) -> None:
        """Remplit une ligne avec le résultat d'un match de bracket."""
        round_label = _BRACKET_ROUND_LABEL.get(match.round_name, "?")
        self._cell(row, 0, round_label, Qt.AlignCenter)
        self._cell(row, 1, "🏆", Qt.AlignCenter)

        players_by_id = {p.id: p for p in self._tournament.players}
        opp_id = (
            match.player2_id
            if match.player1_id == self._player_id
            else match.player1_id
        )
        opp = players_by_id.get(opp_id)
        opp_name = opp.name if opp else "—"

        if not match.finished:
            self._cell(row, 2, "À venir…", Qt.AlignCenter, _COL_MUTED)
            self._cell(row, 3, opp_name, Qt.AlignCenter)
            return

        is_win = match.winner_id == self._player_id
        if is_win:
            self._cell(row, 2, "Victoire", Qt.AlignCenter, _COL_WIN)
        else:
            self._cell(row, 2, "Défaite", Qt.AlignCenter, _COL_LOSS)
        self._cell(row, 3, opp_name, Qt.AlignCenter)
