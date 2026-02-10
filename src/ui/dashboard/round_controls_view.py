from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QSizePolicy
)
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
    export_pdf_requested = Signal()
    projection_requested = Signal()
    quit_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Layout principal vertical
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Ligne des boutons principaux
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)

        # ▶️ Lancer la round
        self.start_round_btn = QPushButton("▶️ Lancer")
        self.start_round_btn.setObjectName("PrimaryButton")
        self.start_round_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.start_round_btn.setMinimumWidth(80)
        self.start_round_btn.setMinimumHeight(38)
        self.start_round_btn.clicked.connect(self.start_round_requested)

        # ⏭ Round suivant
        self.next_round_btn = QPushButton("⏭ Suivant")
        self.next_round_btn.setObjectName("SecondaryButton")
        self.next_round_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.next_round_btn.setMinimumWidth(80)
        self.next_round_btn.setMinimumHeight(38)
        self.next_round_btn.setEnabled(False)
        self.next_round_btn.clicked.connect(self.next_round_requested)

        # 🔀 Round varié (évite répétitions)
        self.shuffle_round_btn = QPushButton("🔀 Varié")
        self.shuffle_round_btn.setObjectName("WarningButton")
        self.shuffle_round_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.shuffle_round_btn.setMinimumWidth(70)
        self.shuffle_round_btn.setMinimumHeight(38)
        self.shuffle_round_btn.setEnabled(False)
        self.shuffle_round_btn.setVisible(False)
        self.shuffle_round_btn.setToolTip("Génère un round en évitant les joueurs déjà rencontrés")
        self.shuffle_round_btn.clicked.connect(self.shuffle_round_requested)

        # 📦 Archiver tournoi (visible quand terminé)
        self.archive_btn = QPushButton("📦 Archiver")
        self.archive_btn.setObjectName("ArchiveButton")
        self.archive_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.archive_btn.setMinimumWidth(80)
        self.archive_btn.setMinimumHeight(38)
        self.archive_btn.setVisible(False)
        self.archive_btn.clicked.connect(self.archive_requested)

        # 📄 Export PDF (visible quand terminé)
        self.export_pdf_btn = QPushButton("📄 PDF")
        self.export_pdf_btn.setObjectName("SecondaryButton")
        self.export_pdf_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.export_pdf_btn.setMinimumWidth(60)
        self.export_pdf_btn.setMinimumHeight(38)
        self.export_pdf_btn.setVisible(False)
        self.export_pdf_btn.clicked.connect(self.export_pdf_requested)

        # 📺 Projection (afficher les pairings)
        self.projection_btn = QPushButton("📺 Projection")
        self.projection_btn.setObjectName("SecondaryButton")
        self.projection_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.projection_btn.setMinimumWidth(90)
        self.projection_btn.setMinimumHeight(38)
        self.projection_btn.setToolTip("Afficher les pairings sur un écran externe")
        self.projection_btn.clicked.connect(self.projection_requested)

        # 🔄 Reset tournoi
        self.reset_btn = QPushButton("🔄 Reset")
        self.reset_btn.setObjectName("DangerButton")
        self.reset_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.reset_btn.setMinimumWidth(70)
        self.reset_btn.setMinimumHeight(38)
        self.reset_btn.clicked.connect(self.reset_requested)

        # 🚪 Quitter le tournoi
        self.quit_btn = QPushButton("🚪 Quitter")
        self.quit_btn.setObjectName("SecondaryButton")
        self.quit_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.quit_btn.setMinimumWidth(70)
        self.quit_btn.setMinimumHeight(38)
        self.quit_btn.clicked.connect(self.quit_requested)

        # Ajouter les boutons au layout
        buttons_layout.addWidget(self.start_round_btn, 1)
        buttons_layout.addWidget(self.next_round_btn, 1)
        buttons_layout.addWidget(self.shuffle_round_btn, 1)
        buttons_layout.addWidget(self.archive_btn, 1)
        buttons_layout.addWidget(self.export_pdf_btn, 1)
        buttons_layout.addWidget(self.projection_btn, 1)
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(self.reset_btn, 1)
        buttons_layout.addWidget(self.quit_btn, 1)

        main_layout.addLayout(buttons_layout)

        # Label d'alerte pour les répétitions (sur une ligne séparée)
        self.repetition_label = QLabel("")
        self.repetition_label.setObjectName("RepetitionWarning")
        self.repetition_label.setVisible(False)
        main_layout.addWidget(self.repetition_label)

    # =====================
    # Public API
    # =====================
    def set_start_enabled(self, enabled: bool):
        self.start_round_btn.setEnabled(enabled)

    def set_next_enabled(self, enabled: bool):
        self.next_round_btn.setEnabled(enabled)

        if enabled:
            self.next_round_btn.setObjectName("PrimaryButton")
        else:
            self.next_round_btn.setObjectName("SecondaryButton")

        # Forcer Qt à réappliquer le style
        self.next_round_btn.style().unpolish(self.next_round_btn)
        self.next_round_btn.style().polish(self.next_round_btn)

    def show_repetition_warning(self, rate: float):
        """Affiche le bouton varié et l'alerte de répétition."""
        self.shuffle_round_btn.setEnabled(True)
        self.shuffle_round_btn.setVisible(True)
        self.repetition_label.setText(f"⚠️ {rate:.0f}% de répétitions dans le prochain round")
        self.repetition_label.setVisible(True)

    def hide_repetition_warning(self):
        """Cache le bouton varié et l'alerte."""
        self.shuffle_round_btn.setEnabled(False)
        self.shuffle_round_btn.setVisible(False)
        self.repetition_label.setVisible(False)

    def show_archive_button(self):
        """Affiche le bouton d'archivage et d'export."""
        self.archive_btn.setVisible(True)
        self.export_pdf_btn.setVisible(True)

    def hide_archive_button(self):
        """Cache le bouton d'archivage et d'export."""
        self.archive_btn.setVisible(False)
        self.export_pdf_btn.setVisible(False)

    def set_swiss_mode(self, enabled: bool):
        """Active/désactive le mode Swiss."""
        if enabled:
            self.next_round_btn.setText("⚖️ Swiss")
            self.shuffle_round_btn.setVisible(False)
            self.shuffle_round_btn.setEnabled(False)
            self.repetition_label.setVisible(False)
        else:
            self.next_round_btn.setText("⏭ Suivant")
