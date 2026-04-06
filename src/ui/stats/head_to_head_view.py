"""Vue des confrontations head-to-head."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QFrame,
    QDialog, QScrollArea
)
from PySide6.QtCore import Qt

from core.stats_analyzer import StatsAnalyzer, MatchupStats


class HeadToHeadView(QWidget):
    """Vue affichant les confrontations entre joueurs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("HeadToHeadView")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._analyzer: StatsAnalyzer | None = None
        self._regular_pseudos: set[str] | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # Sélecteur de joueur
        selector_container = QFrame()
        selector_container.setObjectName("PlayerSelector")
        selector_layout = QHBoxLayout(selector_container)
        selector_layout.setContentsMargins(12, 12, 12, 12)
        selector_layout.setSpacing(12)

        selector_label = QLabel("Joueur :")
        selector_label.setObjectName("PlayerSelectorLabel")

        self.player_combo = QComboBox()
        self.player_combo.setObjectName("PlayerSelectorCombo")
        self.player_combo.setMinimumWidth(250)
        self.player_combo.currentTextChanged.connect(self._on_player_changed)

        selector_layout.addWidget(selector_label)
        selector_layout.addWidget(self.player_combo)
        selector_layout.addStretch()

        layout.addWidget(selector_container)

        # Titre de section
        title = QLabel("Confrontations")
        title.setObjectName("StatsSectionTitle")
        layout.addWidget(title)

        # Table des matchups
        self.table = QTableWidget()
        self.table.setObjectName("MatchupsTable")
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Adversaire", "Matchs", "Victoires", "Défaites", "Winrate"
        ])

        # Configuration
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.doubleClicked.connect(self._on_row_double_clicked)

        # Largeurs des colonnes
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        header.setSectionResizeMode(3, QHeaderView.Fixed)
        header.setSectionResizeMode(4, QHeaderView.Fixed)

        self.table.setColumnWidth(1, 80)
        self.table.setColumnWidth(2, 90)
        self.table.setColumnWidth(3, 90)
        self.table.setColumnWidth(4, 100)

        layout.addWidget(self.table)

        # État vide
        self.empty_label = QLabel("Sélectionnez un joueur pour voir ses confrontations")
        self.empty_label.setObjectName("EmptyState")
        self.empty_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.empty_label)

        # Stocker les matchups pour le double-clic
        self._current_matchups: list[MatchupStats] = []

    def update_stats(self, analyzer: StatsAnalyzer, regular_pseudos: set[str] = None):
        """Met à jour la liste des joueurs (uniquement joueurs réguliers si spécifié)."""
        self._analyzer = analyzer
        self._regular_pseudos = regular_pseudos
        all_players = analyzer.get_all_players()

        # Filtrer pour ne garder que les joueurs réguliers
        if regular_pseudos:
            players = [
                p for p in all_players
                if p.lower().strip() in regular_pseudos
            ]
        else:
            players = all_players

        self.player_combo.blockSignals(True)
        self.player_combo.clear()
        self.player_combo.addItem("-- Sélectionner --")
        for player in players:
            self.player_combo.addItem(player)
        self.player_combo.blockSignals(False)

        self._show_empty_state()

    def _on_player_changed(self, player_name: str):
        """Gère le changement de joueur sélectionné."""
        if not self._analyzer or player_name == "-- Sélectionner --":
            self._show_empty_state()
            return

        all_matchups = self._analyzer.get_player_matchups(player_name)

        # Filtrer pour ne garder que les confrontations avec des joueurs réguliers
        if self._regular_pseudos:
            matchups = [
                m for m in all_matchups
                if m.opponent_name.lower().strip() in self._regular_pseudos
            ]
        else:
            matchups = all_matchups

        self._current_matchups = matchups

        if not matchups:
            self._show_empty_state("Aucune confrontation avec des joueurs réguliers")
            return

        self._show_matchups(matchups)

    def _show_empty_state(self, message: str = "Sélectionnez un joueur pour voir ses confrontations"):
        """Affiche l'état vide."""
        self.table.hide()
        self.empty_label.setText(message)
        self.empty_label.show()
        self._current_matchups = []

    def _show_matchups(self, matchups: list[MatchupStats]):
        """Affiche les confrontations."""
        self.empty_label.hide()
        self.table.show()
        self.table.setRowCount(len(matchups))

        for row, matchup in enumerate(matchups):
            self._populate_row(row, matchup)

    def _populate_row(self, row: int, matchup: MatchupStats):
        """Remplit une ligne du tableau."""
        winrate = matchup.winrate
        winrate_text = f"{winrate:.0f}%"

        # Couleur du winrate
        if winrate >= 60:
            winrate_color = "#3ad68a"  # Vert
        elif winrate >= 40:
            winrate_color = "#f1c40f"  # Jaune
        else:
            winrate_color = "#e94560"  # Rouge

        items = [
            (matchup.opponent_name, Qt.AlignLeft | Qt.AlignVCenter, None),
            (str(matchup.total_matches), Qt.AlignCenter, None),
            (str(matchup.wins), Qt.AlignCenter, "#3ad68a"),
            (str(matchup.losses), Qt.AlignCenter, "#e94560"),
            (winrate_text, Qt.AlignCenter, winrate_color),
        ]

        for col, (text, alignment, color) in enumerate(items):
            item = QTableWidgetItem(text)
            item.setTextAlignment(alignment)
            if color:
                from PySide6.QtGui import QColor
                item.setForeground(QColor(color))
            self.table.setItem(row, col, item)

    def _on_row_double_clicked(self, index):
        """Ouvre le dialogue d'historique pour une confrontation."""
        row = index.row()
        if row < 0 or row >= len(self._current_matchups):
            return

        matchup = self._current_matchups[row]
        player_name = self.player_combo.currentText()

        dialog = MatchupHistoryDialog(self, player_name, matchup)
        dialog.exec()

    def clear(self):
        """Réinitialise l'affichage."""
        self.player_combo.clear()
        self.table.setRowCount(0)
        self._show_empty_state()


class MatchupHistoryDialog(QDialog):
    """Dialogue affichant l'historique des confrontations."""

    def __init__(self, parent, player_name: str, matchup: MatchupStats):
        super().__init__(parent)
        self.setObjectName("MatchupHistoryDialog")
        self.setWindowTitle(f"{player_name} vs {matchup.opponent_name}")
        self.setMinimumSize(500, 400)
        self.setModal(True)

        self._build_ui(player_name, matchup)

    def _build_ui(self, player_name: str, matchup: MatchupStats):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # Titre
        title = QLabel(f"{player_name} vs {matchup.opponent_name}")
        title.setObjectName("MatchupHistoryTitle")
        layout.addWidget(title)

        # Résumé
        summary_container = QFrame()
        summary_container.setObjectName("MatchupSummaryCard")
        summary_layout = QHBoxLayout(summary_container)
        summary_layout.setSpacing(24)

        # Stats résumées
        stats = [
            (str(matchup.total_matches), "Matchs"),
            (str(matchup.wins), "Victoires"),
            (str(matchup.losses), "Défaites"),
            (f"{matchup.winrate:.0f}%", "Winrate"),
        ]

        for value, label in stats:
            stat_widget = QWidget()
            stat_layout = QVBoxLayout(stat_widget)
            stat_layout.setSpacing(4)

            value_label = QLabel(value)
            value_label.setObjectName("MatchupSummaryValue")
            value_label.setAlignment(Qt.AlignCenter)

            # Couleur pour victoires/défaites/winrate
            if label == "Victoires":
                value_label.setStyleSheet("color: #3ad68a;")
            elif label == "Défaites":
                value_label.setStyleSheet("color: #e94560;")
            elif label == "Winrate":
                wr = matchup.winrate
                if wr >= 60:
                    value_label.setStyleSheet("color: #3ad68a;")
                elif wr >= 40:
                    value_label.setStyleSheet("color: #f1c40f;")
                else:
                    value_label.setStyleSheet("color: #e94560;")

            text_label = QLabel(label)
            text_label.setObjectName("MatchupSummaryLabel")
            text_label.setAlignment(Qt.AlignCenter)

            stat_layout.addWidget(value_label)
            stat_layout.addWidget(text_label)
            summary_layout.addWidget(stat_widget)

        layout.addWidget(summary_container)

        # Historique
        history_title = QLabel("Historique des rencontres")
        history_title.setObjectName("StatsSectionTitle")
        layout.addWidget(history_title)

        # Scroll area pour l'historique
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        history_content = QWidget()
        history_layout = QVBoxLayout(history_content)
        history_layout.setContentsMargins(0, 0, 0, 0)
        history_layout.setSpacing(8)

        for result in matchup.history:
            card = QFrame()
            card.setObjectName("HistoryCard")
            card_layout = QHBoxLayout(card)
            card_layout.setContentsMargins(12, 12, 12, 12)

            # Info tournoi
            info_widget = QWidget()
            info_layout = QVBoxLayout(info_widget)
            info_layout.setContentsMargins(0, 0, 0, 0)
            info_layout.setSpacing(2)

            name_label = QLabel(result.tournament_name)
            name_label.setObjectName("HistoryTournamentName")

            if result.is_bracket:
                detail = f"{result.tournament_date} — {result.bracket_round_name} 🏆"
            else:
                detail = f"{result.tournament_date} — Round {result.round_number}, Table {result.table_number}"
            date_label = QLabel(detail)
            date_label.setObjectName("HistoryDate")

            info_layout.addWidget(name_label)
            info_layout.addWidget(date_label)

            # Résultat
            if result.is_win:
                result_text = "Victoire"
                result_color = "#3ad68a"
            elif result.is_loss:
                result_text = "Défaite"
                result_color = "#e94560"
            else:
                result_text = "Égalité"
                result_color = "#f1c40f"

            if result.is_bracket:
                result_label = QLabel(result_text)
            else:
                result_label = QLabel(f"{result_text} ({result.player_position}e vs {result.opponent_position}e)")
            result_label.setObjectName("HistoryResult")
            result_label.setStyleSheet(f"color: {result_color};")
            result_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            card_layout.addWidget(info_widget, 1)
            card_layout.addWidget(result_label)

            history_layout.addWidget(card)

        history_layout.addStretch()
        scroll.setWidget(history_content)
        layout.addWidget(scroll)
