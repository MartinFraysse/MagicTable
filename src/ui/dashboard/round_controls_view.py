from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Signal


class DashboardRoundControlsView(QWidget):
    """
    Zone de contrôle de la round :
    - ▶️ Lancer la round (one-shot)
    - ⏭ Round suivant
    - 🔀 Round varié (évite les répétitions)
    - 🔄 Reset tournoi
    """

    start_round_requested = Signal()
    next_round_requested = Signal()
    shuffle_round_requested = Signal()
    reset_requested = Signal()
    archive_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)

        # ▶️ Lancer la round
        self.start_round_btn = QPushButton("▶️ Lancer la round")
        self.start_round_btn.setObjectName("PrimaryButton")
        self.start_round_btn.clicked.connect(self.start_round_requested)

        # ⏭ Round suivant
        self.next_round_btn = QPushButton("⏭ Round suivant")
        self.next_round_btn.setObjectName("SecondaryButton")
        self.next_round_btn.setEnabled(False)
        self.next_round_btn.clicked.connect(self.next_round_requested)

        # 🔀 Round varié (évite répétitions)
        self.shuffle_round_btn = QPushButton("🔀 Round varié")
        self.shuffle_round_btn.setObjectName("WarningButton")
        self.shuffle_round_btn.setEnabled(False)
        self.shuffle_round_btn.setVisible(False)
        self.shuffle_round_btn.setToolTip("Génère un round en évitant les joueurs déjà rencontrés")
        self.shuffle_round_btn.clicked.connect(self.shuffle_round_requested)

        # Label d'alerte pour les répétitions
        self.repetition_label = QLabel("")
        self.repetition_label.setObjectName("RepetitionWarning")
        self.repetition_label.setVisible(False)

        # 📦 Archiver tournoi (visible quand terminé)
        self.archive_btn = QPushButton("📦 Archiver")
        self.archive_btn.setObjectName("ArchiveButton")
        self.archive_btn.setVisible(False)
        self.archive_btn.clicked.connect(self.archive_requested)

        # 🔄 Reset tournoi
        self.reset_btn = QPushButton("🔄 Reset")
        self.reset_btn.setObjectName("DangerButton")
        self.reset_btn.clicked.connect(self.reset_requested)

        layout.addWidget(self.start_round_btn)
        layout.addWidget(self.next_round_btn)
        layout.addWidget(self.shuffle_round_btn)
        layout.addWidget(self.repetition_label)
        layout.addWidget(self.archive_btn)
        layout.addStretch()
        layout.addWidget(self.reset_btn)

    # =====================
    # Public API
    # =====================
    def set_start_enabled(self, enabled: bool):
        self.start_round_btn.setEnabled(enabled)

    def set_next_enabled(self, enabled: bool):
        self.next_round_btn.setEnabled(enabled)

        if enabled:
            # 🔥 Devient un bouton principal
            self.next_round_btn.setObjectName("PrimaryButton")
        else:
            # Reviens en bouton secondaire
            self.next_round_btn.setObjectName("SecondaryButton")

        # Forcer Qt à réappliquer le style
        self.next_round_btn.style().unpolish(self.next_round_btn)
        self.next_round_btn.style().polish(self.next_round_btn)

    def show_repetition_warning(self, rate: float):
        """Affiche le bouton varié et l'alerte de répétition."""
        self.shuffle_round_btn.setEnabled(True)
        self.shuffle_round_btn.setVisible(True)
        self.repetition_label.setText(f"⚠️ {rate:.0f}% de répétitions")
        self.repetition_label.setVisible(True)

    def hide_repetition_warning(self):
        """Cache le bouton varié et l'alerte."""
        self.shuffle_round_btn.setEnabled(False)
        self.shuffle_round_btn.setVisible(False)
        self.repetition_label.setVisible(False)

    def show_archive_button(self):
        """Affiche le bouton d'archivage."""
        self.archive_btn.setVisible(True)

    def hide_archive_button(self):
        """Cache le bouton d'archivage."""
        self.archive_btn.setVisible(False)

