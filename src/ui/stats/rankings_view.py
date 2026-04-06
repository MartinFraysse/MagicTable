"""Vue du classement des joueurs."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QLabel,
)
from PySide6.QtCore import Qt

from core.stats_analyzer import StatsAnalyzer, PlayerStats


class RankingsView(QWidget):
    """Vue affichant le classement des joueurs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("RankingsView")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._players: list[PlayerStats] = []

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Titre
        title = QLabel("Classement des joueurs")
        title.setObjectName("StatsSectionTitle")
        layout.addWidget(title)

        # Table
        self.table = QTableWidget()
        self.table.setObjectName("MatchupsTable")
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "#", "Joueur", "Points", "Tournois", "Podiums", "Top 1", "Top 2", "Top 3"
        ])

        # Configuration
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)

        # Largeurs des colonnes
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.Fixed)
        header.setSectionResizeMode(5, QHeaderView.Fixed)
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        header.setSectionResizeMode(7, QHeaderView.Fixed)

        self.table.setColumnWidth(0, 50)   # #
        self.table.setColumnWidth(2, 80)   # Points
        self.table.setColumnWidth(3, 90)   # Tournois
        self.table.setColumnWidth(4, 90)   # Podiums
        self.table.setColumnWidth(5, 70)   # Top 1
        self.table.setColumnWidth(6, 70)   # Top 2
        self.table.setColumnWidth(7, 70)   # Top 3

        layout.addWidget(self.table)

        # État vide
        self.empty_label = QLabel("Aucun tournoi archivé")
        self.empty_label.setObjectName("EmptyState")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.hide()
        layout.addWidget(self.empty_label)

    def update_stats(self, analyzer: StatsAnalyzer, regular_pseudos: set[str] = None):
        """Met à jour le classement (uniquement joueurs réguliers si spécifié)."""
        all_players = analyzer.get_top_players(limit=100)

        # Filtrer pour ne garder que les joueurs réguliers
        if regular_pseudos:
            players = [
                p for p in all_players
                if p.name.lower().strip() in regular_pseudos
            ]
        else:
            players = all_players

        self._players = players

        if not players:
            self.table.hide()
            self.empty_label.setText("Aucun joueur régulier dans les tournois archivés")
            self.empty_label.show()
            return

        self.empty_label.hide()
        self.table.show()
        self.table.setRowCount(len(players))

        for row, player in enumerate(players):
            self._populate_row(row, player)

    def _populate_row(self, row: int, player: PlayerStats):
        """Remplit une ligne du tableau."""
        rank = row + 1

        # Médaille pour le top 3
        rank_text = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, str(rank))

        items = [
            (rank_text, Qt.AlignCenter),
            (player.name, Qt.AlignLeft | Qt.AlignVCenter),
            (str(player.total_points), Qt.AlignCenter),
            (str(player.tournaments_played), Qt.AlignCenter),
            (str(player.total_podiums), Qt.AlignCenter),
            (str(player.top_1), Qt.AlignCenter),
            (str(player.top_2), Qt.AlignCenter),
            (str(player.top_3), Qt.AlignCenter),
        ]

        for col, (text, alignment) in enumerate(items):
            item = QTableWidgetItem(text)
            item.setTextAlignment(alignment)

            # Couleurs spéciales pour le podium
            if rank == 1:
                item.setForeground(Qt.GlobalColor.yellow)
            elif rank == 2:
                item.setForeground(Qt.GlobalColor.lightGray)
            elif rank == 3:
                item.setForeground(Qt.GlobalColor.darkYellow)

            self.table.setItem(row, col, item)

    def clear(self):
        """Réinitialise l'affichage."""
        self._players = []
        self.table.setRowCount(0)
        self.table.hide()
        self.empty_label.show()


