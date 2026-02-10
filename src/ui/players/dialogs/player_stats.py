from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QGridLayout,
)

from core.regular_player import RegularPlayer


class PlayerStatsDialog(QDialog):
    """Dialog affichant les statistiques d'un joueur."""

    def __init__(self, parent, player: RegularPlayer):
        super().__init__(parent)

        self.setWindowTitle(f"Statistiques — {player.pseudo}")
        self.setModal(True)
        self.setMinimumSize(400, 450)
        self.setObjectName("PlayerStatsDialog")

        self._player = player

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(24, 24, 24, 24)

        # Titre avec pseudo
        title = QLabel(f"📊 {self._player.pseudo}")
        title.setObjectName("DialogTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Nom complet si présent
        if self._player.full_name:
            subtitle = QLabel(self._player.full_name)
            subtitle.setObjectName("DialogSubtitle")
            subtitle.setAlignment(Qt.AlignCenter)
            layout.addWidget(subtitle)

        # Section Podiums
        podiums_frame = self._build_podiums_section()
        layout.addWidget(podiums_frame)

        # Section Stats générales
        stats_frame = self._build_stats_section()
        layout.addWidget(stats_frame)

        layout.addStretch()

        # Bouton fermer
        close_btn = QPushButton("Fermer")
        close_btn.setObjectName("CancelButton")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)

    def _build_podiums_section(self) -> QFrame:
        """Construit la section des podiums."""
        frame = QFrame()
        frame.setObjectName("StatsSection")

        layout = QVBoxLayout(frame)
        layout.setSpacing(16)

        section_title = QLabel("Podiums")
        section_title.setObjectName("StatsSectionTitle")
        layout.addWidget(section_title)

        # Grille des podiums
        podiums_layout = QHBoxLayout()
        podiums_layout.setSpacing(20)

        podiums_data = [
            ("🥇", "1ère place", self._player.top_1),
            ("🥈", "2ème place", self._player.top_2),
            ("🥉", "3ème place", self._player.top_3),
        ]

        for emoji, label, count in podiums_data:
            podium_widget = self._build_podium_card(emoji, label, count)
            podiums_layout.addWidget(podium_widget)

        layout.addLayout(podiums_layout)

        # Total podiums
        total_layout = QHBoxLayout()
        total_label = QLabel("Total podiums")
        total_label.setObjectName("StatsTotalLabel")
        total_value = QLabel(str(self._player.total_podiums))
        total_value.setObjectName("StatsTotalValue")

        total_layout.addWidget(total_label)
        total_layout.addStretch()
        total_layout.addWidget(total_value)

        layout.addLayout(total_layout)

        return frame

    def _build_podium_card(self, emoji: str, label: str, count: int) -> QFrame:
        """Construit une carte pour un type de podium."""
        card = QFrame()
        card.setObjectName("PodiumCard")

        layout = QVBoxLayout(card)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignCenter)

        emoji_label = QLabel(emoji)
        emoji_label.setObjectName("PodiumEmoji")
        emoji_label.setAlignment(Qt.AlignCenter)

        count_label = QLabel(str(count))
        count_label.setObjectName("PodiumCount")
        count_label.setAlignment(Qt.AlignCenter)

        text_label = QLabel(label)
        text_label.setObjectName("PodiumLabel")
        text_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(emoji_label)
        layout.addWidget(count_label)
        layout.addWidget(text_label)

        return card

    def _build_stats_section(self) -> QFrame:
        """Construit la section des statistiques générales."""
        frame = QFrame()
        frame.setObjectName("StatsSection")

        layout = QVBoxLayout(frame)
        layout.setSpacing(12)

        section_title = QLabel("Informations")
        section_title.setObjectName("StatsSectionTitle")
        layout.addWidget(section_title)

        # Grille des stats
        grid = QGridLayout()
        grid.setSpacing(8)

        stats = [
            ("Tournois joués", str(self._player.tournaments_played)),
            ("Points", str(self._player.points)),
            ("Téléphone", self._format_phone(self._player.phone) if self._player.phone else "—"),
        ]

        for row, (label, value) in enumerate(stats):
            label_widget = QLabel(label)
            label_widget.setObjectName("StatsLabel")

            value_widget = QLabel(value)
            value_widget.setObjectName("StatsValue")

            grid.addWidget(label_widget, row, 0)
            grid.addWidget(value_widget, row, 1)

        layout.addLayout(grid)

        return frame

    def _format_phone(self, phone: str) -> str:
        """Formate le numéro de téléphone."""
        digits = ''.join(c for c in phone if c.isdigit())
        if len(digits) == 10:
            return ' '.join(digits[i:i+2] for i in range(0, 10, 2))
        return phone
