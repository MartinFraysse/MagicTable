"""Vue des statistiques des commandants."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QDialog,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from core.stats_analyzer import StatsAnalyzer, CommanderStats, CommanderMatchup
from core.theme_manager import theme_manager


class CommandersView(QWidget):
    """Vue affichant les win rates de tous les commandants par format."""

    _FORMATS = [
        ("👑 Commander",      "👑 Commander Multi"),
        ("⚔️ Duel Commander", "⚔️ Duel Commander"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CommandersView")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setObjectName("CommandersScroll")

        content = QWidget()
        content.setAttribute(Qt.WA_StyledBackground, True)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(24)

        title = QLabel("Win Rate des Commandants")
        title.setObjectName("StatsSectionTitle")
        content_layout.addWidget(title)

        self._format_widgets: dict[str, _FormatSection] = {}
        for fmt_key, fmt_label in self._FORMATS:
            section = _FormatSection(fmt_label, fmt_key)
            self._format_widgets[fmt_key] = section
            content_layout.addWidget(section)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

    def update_stats(self, analyzer: StatsAnalyzer):
        for fmt_key, _ in self._FORMATS:
            stats = analyzer.get_global_commander_stats(fmt_key)
            self._format_widgets[fmt_key].set_data(stats, analyzer)


class _FormatSection(QFrame):
    """Section pour un format Commander (Multi ou Duel)."""

    def __init__(self, title: str, fmt_key: str, parent=None):
        super().__init__(parent)
        self.setObjectName("ChartContainer")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._fmt_key = fmt_key
        self._analyzer: StatsAnalyzer | None = None
        self._stats: list[CommanderStats] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # En-tête : titre + compteur
        header = QHBoxLayout()
        header.setSpacing(12)

        self._title_label = QLabel(title)
        self._title_label.setObjectName("StatsSectionTitle")

        self._count_label = QLabel("")
        self._count_label.setObjectName("CountLabel")

        header.addWidget(self._title_label)
        header.addWidget(self._count_label)
        header.addStretch()
        layout.addLayout(header)

        hint = QLabel("Double-cliquez sur un commandant pour voir ses confrontations")
        hint.setObjectName("StatsHint")
        layout.addWidget(hint)

        # Tableau
        self._table = QTableWidget()
        self._table.setObjectName("MatchupsTable")
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(
            ["Commandant", "Matchs", "Victoires", "Win%", "1er 🥇", "2e 🥈", "3e 🥉"]
        )
        self._table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.verticalHeader().setVisible(False)
        self._table.setShowGrid(False)
        self._table.setAlternatingRowColors(False)

        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, 7):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeToContents)

        layout.addWidget(self._table)

        # État vide
        self._empty_label = QLabel("Aucun commandant enregistré pour ce format")
        self._empty_label.setObjectName("EmptyState")
        self._empty_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._empty_label)
        self._empty_label.hide()

        self._table.doubleClicked.connect(self._on_double_click)

    def set_data(self, stats: list[CommanderStats], analyzer: StatsAnalyzer):
        self._stats = stats
        self._analyzer = analyzer

        if not stats:
            self._table.hide()
            self._count_label.setText("")
            self._empty_label.show()
            return

        self._empty_label.hide()
        self._table.show()
        self._count_label.setText(f"({len(stats)})")

        self._table.setRowCount(len(stats))
        for row, s in enumerate(stats):
            data = [
                (s.commander_name,        Qt.AlignLeft | Qt.AlignVCenter),
                (str(s.matches_played),   Qt.AlignCenter),
                (str(s.matches_won),      Qt.AlignCenter),
                (f"{s.winrate:.0f}%",     Qt.AlignCenter),
                (str(s.top1),             Qt.AlignCenter),
                (str(s.top2),             Qt.AlignCenter),
                (str(s.top3),             Qt.AlignCenter),
            ]
            for col, (text, align) in enumerate(data):
                item = QTableWidgetItem(text)
                item.setTextAlignment(align)
                if col == 3:
                    item.setForeground(_winrate_color(s.winrate))
                self._table.setItem(row, col, item)

        self._table.resizeRowsToContents()
        row_h = self._table.rowHeight(0)
        hdr_h = self._table.horizontalHeader().height()
        self._table.setFixedHeight(hdr_h + row_h * len(stats) + 4)

    def _on_double_click(self, index):
        row = index.row()
        if row < 0 or row >= len(self._stats) or self._analyzer is None:
            return
        s = self._stats[row]
        matchups = self._analyzer.get_commander_matchups(s.commander_name, self._fmt_key)
        dialog = CommanderMatchupsDialog(self, s.commander_name, matchups)
        dialog.exec()


class CommanderMatchupsDialog(QDialog):
    """Dialog compact affichant les confrontations d'un commandant contre les autres."""

    _MAX_VISIBLE_ROWS = 8

    def __init__(self, parent, commander_name: str, matchups: list[CommanderMatchup]):
        super().__init__(parent)
        self.setObjectName("CommanderMatchupsDialog")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setWindowTitle(commander_name)
        self.setModal(True)
        self.setSizeGripEnabled(False)
        self.setFixedSize(400, 360)

        # Couleurs selon le thème actif
        is_dark = theme_manager.get_theme() == "dark"
        if is_dark:
            bg       = "#1a3d32"
            bg_table = "#132f26"
            bg_hdr   = "#1c4a3a"
            fg       = "#eafff6"
            fg_sub   = "#b6dcd0"
            border   = "#2f6f55"
            accent   = "#3ad68a"
            hover    = "#245f4a"
        else:
            bg       = "#f0faf7"
            bg_table = "#ffffff"
            bg_hdr   = "#e8f8f2"
            fg       = "#1a3d33"
            fg_sub   = "#3d6b5e"
            border   = "#c0e0d5"
            accent   = "#2eaa6e"
            hover    = "#e0f5ed"

        self.setStyleSheet(f"""
            CommanderMatchupsDialog {{
                background-color: {bg};
            }}
            #CmdMatchupTitle {{
                color: {fg};
                font-size: 15px;
                font-weight: 700;
            }}
            #CmdMatchupSummary {{
                color: {fg_sub};
                font-size: 12px;
            }}
            #CmdMatchupSep {{
                background-color: {border};
                max-height: 1px;
                border: none;
            }}
            #CmdMatchupTable {{
                background-color: {bg_table};
                color: {fg};
                font-size: 13px;
                border: none;
                outline: none;
            }}
            #CmdMatchupTable::item {{
                padding: 4px 8px;
                background-color: transparent;
            }}
            #CmdMatchupTable::item:hover {{
                background-color: {hover};
            }}
            #CmdMatchupTable QHeaderView::section {{
                background-color: {bg_hdr};
                color: {accent};
                font-size: 11px;
                font-weight: 700;
                border: none;
                border-bottom: 1px solid {accent};
                padding: 4px 8px;
            }}
            QAbstractScrollArea::viewport {{
                background-color: {bg_table};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(6)

        # Titre
        title = QLabel(f"⚔️  {commander_name}")
        title.setObjectName("CmdMatchupTitle")
        title.setWordWrap(True)
        layout.addWidget(title)

        if not matchups:
            empty = QLabel("Aucune confrontation enregistrée")
            empty.setObjectName("EmptyState")
            empty.setAlignment(Qt.AlignCenter)
            layout.addWidget(empty)
            return

        # Résumé en une ligne
        total_played = sum(m.matches_played for m in matchups)
        total_won = sum(m.matches_won for m in matchups)
        global_rate = (total_won / total_played * 100) if total_played else 0

        summary = QLabel(
            f"{total_played} matchs  ·  {total_won} victoires  ·  {global_rate:.0f}% win rate"
        )
        summary.setObjectName("CmdMatchupSummary")
        layout.addWidget(summary)

        # Séparateur
        sep = QFrame()
        sep.setObjectName("CmdMatchupSep")
        sep.setFrameShape(QFrame.HLine)
        layout.addWidget(sep)

        # Table
        table = QTableWidget()
        table.setObjectName("CmdMatchupTable")
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Commandant adverse", "Matchs", "Victoires", "Win%"])
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.NoSelection)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setAlternatingRowColors(False)
        table.setFrameShape(QFrame.NoFrame)

        hdr = table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, 4):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeToContents)

        table.setRowCount(len(matchups))
        for row, m in enumerate(matchups):
            data = [
                (m.opponent_commander,  Qt.AlignLeft | Qt.AlignVCenter),
                (str(m.matches_played), Qt.AlignCenter),
                (str(m.matches_won),    Qt.AlignCenter),
                (f"{m.winrate:.0f}%",   Qt.AlignCenter),
            ]
            for col, (text, align) in enumerate(data):
                item = QTableWidgetItem(text)
                item.setTextAlignment(align)
                if col == 3:
                    item.setForeground(_winrate_color(m.winrate))
                table.setItem(row, col, item)

        table.resizeRowsToContents()

        layout.addWidget(table)


def _winrate_color(rate: float) -> QColor:
    if rate >= 60:
        return QColor("#3ad68a")
    if rate >= 40:
        return QColor("#f5d76e")
    return QColor("#e07070")
