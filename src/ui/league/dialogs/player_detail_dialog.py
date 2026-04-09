"""Dialog affichant l'historique d'un joueur dans une ligue."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton,
)
from PySide6.QtCore import Qt

from core.league import League, LeagueStandingEntry, get_player_league_history
from core.tournament import Tournament


class PlayerDetailDialog(QDialog):
    def __init__(
        self,
        parent,
        entry: LeagueStandingEntry,
        league: League,
        tournaments: list[Tournament],
    ):
        super().__init__(parent)
        self.setWindowTitle(entry.player_name)
        self.setMinimumWidth(480)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("PlayerDetailDialog")

        self._history = get_player_league_history(league, entry.player_name, tournaments)

        self._build_ui(entry, league)

    def _build_ui(self, entry: LeagueStandingEntry, league: League) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(24, 24, 24, 24)

        # ── En-tête ──────────────────────────────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(14)

        medals = {1: "🥇", 2: "🥈", 3: "🥉"}
        rank_lbl = QLabel(medals.get(entry.rank, f"#{entry.rank}"))
        rank_lbl.setObjectName("PlayerDetailRank")

        name_col = QVBoxLayout()
        name_col.setSpacing(3)

        name_lbl = QLabel(entry.player_name)
        name_lbl.setObjectName("PlayerDetailName")

        sub = QLabel(
            f"{entry.total_points} pts  •  "
            f"{entry.tournaments_played} tournoi(s)  •  "
            f"Meilleur : {medals.get(entry.best_result, f'#{entry.best_result}')}"
        )
        sub.setObjectName("PlayerDetailSub")

        name_col.addWidget(name_lbl)
        name_col.addWidget(sub)

        header.addWidget(rank_lbl)
        header.addLayout(name_col)
        header.addStretch()
        root.addLayout(header)

        # ── Séparateur ───────────────────────────────────────────────────────
        sep_lbl = QLabel("Historique des tournois")
        sep_lbl.setObjectName("LeagueSectionTitle")
        root.addWidget(sep_lbl)

        # ── Tableau historique ────────────────────────────────────────────────
        table = QTableWidget(len(self._history), 4)
        table.setObjectName("PlayerDetailTable")
        table.setHorizontalHeaderLabels(["Tournoi", "Date", "Position", "Points"])

        hh = table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSelectionMode(QTableWidget.NoSelection)
        table.setAlternatingRowColors(True)

        for row, (t, rank, pts) in enumerate(self._history):
            pos_str = medals.get(rank, f"#{rank}")

            items = [
                (t.name,    Qt.AlignLeft | Qt.AlignVCenter),
                (t.date,    Qt.AlignCenter),
                (pos_str,   Qt.AlignCenter),
                (f"{pts} pts", Qt.AlignCenter),
            ]
            for col, (val, align) in enumerate(items):
                item = QTableWidgetItem(val)
                item.setTextAlignment(align)
                table.setItem(row, col, item)

        if not self._history:
            table.setRowCount(1)
            placeholder = QTableWidgetItem("Aucun tournoi archivé pour ce joueur")
            placeholder.setTextAlignment(Qt.AlignCenter)
            placeholder.setFlags(Qt.NoItemFlags)
            table.setItem(0, 0, placeholder)
            table.setSpan(0, 0, 1, 4)

        root.addWidget(table, 1)

        # ── Fermer ───────────────────────────────────────────────────────────
        close_btn = QPushButton("Fermer")
        close_btn.setObjectName("SecondaryButton")
        close_btn.setFixedHeight(36)
        close_btn.clicked.connect(self.accept)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        root.addLayout(btn_row)
