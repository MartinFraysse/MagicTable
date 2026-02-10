"""Vue des statistiques globales."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QProgressBar
)
from PySide6.QtCore import Qt

from core.stats_analyzer import StatsAnalyzer


class GlobalStatsView(QWidget):
    """Vue affichant les statistiques globales des tournois."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GlobalStatsView")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        content.setAttribute(Qt.WA_StyledBackground, True)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(24)

        # Section titre
        title = QLabel("Vue d'ensemble")
        title.setObjectName("StatsSectionTitle")
        content_layout.addWidget(title)

        # Tuiles KPI
        self.tiles_container = QHBoxLayout()
        self.tiles_container.setSpacing(16)

        self.tile_tournaments = self._create_tile("0", "Tournois joués")
        self.tile_players = self._create_tile("0", "Joueurs uniques")
        self.tile_tables = self._create_tile("0", "Tables jouées")

        self.tiles_container.addWidget(self.tile_tournaments)
        self.tiles_container.addWidget(self.tile_players)
        self.tiles_container.addWidget(self.tile_tables)
        self.tiles_container.addStretch()

        content_layout.addLayout(self.tiles_container)

        # Section distribution des formats
        format_title = QLabel("Distribution des formats")
        format_title.setObjectName("StatsSectionTitle")
        content_layout.addWidget(format_title)

        self.format_container = QWidget()
        self.format_container.setObjectName("ChartContainer")
        self.format_layout = QVBoxLayout(self.format_container)
        self.format_layout.setContentsMargins(16, 16, 16, 16)
        self.format_layout.setSpacing(12)

        content_layout.addWidget(self.format_container)
        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

    def _create_tile(self, value: str, label: str) -> QWidget:
        """Crée une tuile de statistique."""
        tile = QFrame()
        tile.setObjectName("StatsTile")
        tile.setAttribute(Qt.WA_StyledBackground, True)

        layout = QVBoxLayout(tile)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(4)

        value_label = QLabel(value)
        value_label.setObjectName("StatsTileValue")
        value_label.setAlignment(Qt.AlignCenter)

        text_label = QLabel(label)
        text_label.setObjectName("StatsTileLabel")
        text_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(value_label)
        layout.addWidget(text_label)

        # Stocker la référence pour mise à jour
        tile.value_label = value_label

        return tile

    def update_stats(self, analyzer: StatsAnalyzer):
        """Met à jour les statistiques affichées."""
        global_stats = analyzer.get_global_stats()

        # Mettre à jour les tuiles
        self.tile_tournaments.value_label.setText(str(global_stats["total_tournaments"]))
        self.tile_players.value_label.setText(str(global_stats["total_unique_players"]))
        self.tile_tables.value_label.setText(str(global_stats["total_tables"]))

        # Mettre à jour la distribution des formats
        self._update_format_distribution(analyzer.get_format_distribution())

    def _update_format_distribution(self, distribution: dict[str, int]):
        """Met à jour l'affichage de la distribution des formats."""
        # Vider le conteneur
        while self.format_layout.count():
            item = self.format_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not distribution:
            empty_label = QLabel("Aucun tournoi archivé")
            empty_label.setObjectName("EmptyState")
            empty_label.setAlignment(Qt.AlignCenter)
            self.format_layout.addWidget(empty_label)
            return

        total = sum(distribution.values())

        for format_name, count in sorted(distribution.items(), key=lambda x: -x[1]):
            percentage = (count / total * 100) if total > 0 else 0

            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(12)

            # Nom du format
            name_label = QLabel(format_name)
            name_label.setStyleSheet("color: #eafff6; font-size: 14px; font-weight: 500;")
            name_label.setMinimumWidth(150)

            # Barre de progression
            progress_bar = QProgressBar()
            progress_bar.setMinimum(0)
            progress_bar.setMaximum(100)
            progress_bar.setValue(int(percentage))
            progress_bar.setTextVisible(False)
            progress_bar.setFixedHeight(24)
            progress_bar.setStyleSheet("""
                QProgressBar {
                    background-color: #1c4a3a;
                    border-radius: 4px;
                    border: none;
                }
                QProgressBar::chunk {
                    background-color: #3ad68a;
                    border-radius: 4px;
                }
            """)

            # Valeur
            value_label = QLabel(f"{count} ({percentage:.0f}%)")
            value_label.setStyleSheet("color: #b6dcd0; font-size: 13px;")
            value_label.setMinimumWidth(80)
            value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            row_layout.addWidget(name_label)
            row_layout.addWidget(progress_bar, 1)
            row_layout.addWidget(value_label)

            self.format_layout.addWidget(row)

    def clear(self):
        """Réinitialise l'affichage."""
        self.tile_tournaments.value_label.setText("0")
        self.tile_players.value_label.setText("0")
        self.tile_tables.value_label.setText("0")

        while self.format_layout.count():
            item = self.format_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
