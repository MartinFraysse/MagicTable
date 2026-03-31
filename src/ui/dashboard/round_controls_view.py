from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QSizePolicy
)
from PySide6.QtCore import Signal


class DashboardRoundControlsView(QWidget):
    """
    Zone de contrôle du round — deux lignes de boutons :

    Ligne 1 (flux du tournoi) :
      ▶ Lancer  |  ⏭ Round suivante  |  ✏ Modifier pairings  |  🔀 Round varié
      stretch  |  📦 Archiver  |  📄 Exporter PDF

    Ligne 2 (outils) :
      📺 Projection  |  stretch  |  🔄 Réinitialiser  |  🚪 Quitter le tournoi
    """

    start_round_requested    = Signal()
    next_round_requested     = Signal()
    shuffle_round_requested  = Signal()
    edit_pairings_requested  = Signal()
    launch_bracket_requested = Signal()
    reset_requested          = Signal()
    archive_requested        = Signal()
    export_pdf_requested     = Signal()
    projection_requested     = Signal()
    quit_requested           = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # ── LIGNE 1 ──────────────────────────────────────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(8)

        # ▶ Lancer le round
        self.start_round_btn = QPushButton("▶  Lancer le round")
        self.start_round_btn.setObjectName("PrimaryButton")
        self.start_round_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.start_round_btn.setMinimumHeight(38)
        self.start_round_btn.clicked.connect(self.start_round_requested)

        # ⏭ Round suivante / 🏁 Terminer
        self.next_round_btn = QPushButton("⏭  Round suivante")
        self.next_round_btn.setObjectName("SecondaryButton")
        self.next_round_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.next_round_btn.setMinimumHeight(38)
        self.next_round_btn.setEnabled(False)
        self.next_round_btn.clicked.connect(self.next_round_requested)

        # ✏ Modifier les pairings (round 1 uniquement)
        self.edit_pairings_btn = QPushButton("✏️  Modifier les pairings")
        self.edit_pairings_btn.setObjectName("SecondaryButton")
        self.edit_pairings_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.edit_pairings_btn.setMinimumHeight(38)
        self.edit_pairings_btn.setVisible(False)
        self.edit_pairings_btn.clicked.connect(self.edit_pairings_requested)

        # 🔀 Round varié (évite répétitions, formats non-Swiss)
        self.shuffle_round_btn = QPushButton("🔀  Round varié")
        self.shuffle_round_btn.setObjectName("WarningButton")
        self.shuffle_round_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.shuffle_round_btn.setMinimumHeight(38)
        self.shuffle_round_btn.setEnabled(False)
        self.shuffle_round_btn.setVisible(False)
        self.shuffle_round_btn.clicked.connect(self.shuffle_round_requested)

        # 🏆 Lancer le bracket (visible après dernier round Swiss)
        self.launch_bracket_btn = QPushButton("🏆  Lancer le bracket")
        self.launch_bracket_btn.setObjectName("BracketButton")
        self.launch_bracket_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.launch_bracket_btn.setMinimumHeight(38)
        self.launch_bracket_btn.setVisible(False)
        self.launch_bracket_btn.clicked.connect(self.launch_bracket_requested)

        # 📦 Archiver (visible quand terminé)
        self.archive_btn = QPushButton("📦  Archiver le tournoi")
        self.archive_btn.setObjectName("ArchiveButton")
        self.archive_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.archive_btn.setMinimumHeight(38)
        self.archive_btn.setVisible(False)
        self.archive_btn.clicked.connect(self.archive_requested)

        # 📄 Exporter PDF (visible quand terminé)
        self.export_pdf_btn = QPushButton("📄  Exporter PDF")
        self.export_pdf_btn.setObjectName("SecondaryButton")
        self.export_pdf_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.export_pdf_btn.setMinimumHeight(38)
        self.export_pdf_btn.setVisible(False)
        self.export_pdf_btn.clicked.connect(self.export_pdf_requested)

        row1.addWidget(self.start_round_btn)
        row1.addWidget(self.next_round_btn)
        row1.addWidget(self.edit_pairings_btn)
        row1.addWidget(self.shuffle_round_btn)
        row1.addWidget(self.launch_bracket_btn)
        row1.addStretch(1)
        row1.addWidget(self.archive_btn)
        row1.addWidget(self.export_pdf_btn)

        # ── LIGNE 2 ──────────────────────────────────────────────────
        row2 = QHBoxLayout()
        row2.setSpacing(8)

        # 📺 Projection
        self.projection_btn = QPushButton("📺  Afficher la projection")
        self.projection_btn.setObjectName("SecondaryButton")
        self.projection_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.projection_btn.setMinimumHeight(34)
        self.projection_btn.clicked.connect(self.projection_requested)

        # 🔄 Réinitialiser
        self.reset_btn = QPushButton("🔄  Réinitialiser le tournoi")
        self.reset_btn.setObjectName("DangerButton")
        self.reset_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.reset_btn.setMinimumHeight(34)
        self.reset_btn.clicked.connect(self.reset_requested)

        # 🚪 Quitter
        self.quit_btn = QPushButton("🚪  Quitter le tournoi")
        self.quit_btn.setObjectName("SecondaryButton")
        self.quit_btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.quit_btn.setMinimumHeight(34)
        self.quit_btn.clicked.connect(self.quit_requested)

        row2.addWidget(self.projection_btn)
        row2.addStretch(1)
        row2.addWidget(self.reset_btn)
        row2.addWidget(self.quit_btn)

        # ── LABEL AVERTISSEMENT RÉPÉTITIONS ──────────────────────────
        self.repetition_label = QLabel("")
        self.repetition_label.setObjectName("RepetitionWarning")
        self.repetition_label.setVisible(False)

        main_layout.addLayout(row1)
        main_layout.addWidget(self.repetition_label)
        main_layout.addLayout(row2)

    # =====================
    # Public API
    # =====================
    def set_start_enabled(self, enabled: bool):
        self.start_round_btn.setEnabled(enabled)

    def set_next_enabled(self, enabled: bool):
        self.next_round_btn.setEnabled(enabled)
        self.next_round_btn.setObjectName("PrimaryButton" if enabled else "SecondaryButton")
        self.next_round_btn.style().unpolish(self.next_round_btn)
        self.next_round_btn.style().polish(self.next_round_btn)

    def set_finish_mode(self, enabled: bool):
        """Transforme le bouton 'Round suivante' en 'Terminer le tournoi' (dernier round)."""
        if enabled:
            self.next_round_btn.setText("🏁  Terminer le tournoi")
            self.next_round_btn.setObjectName("FinishButton")
        else:
            self.next_round_btn.setText("⏭  Round suivante")
            self.next_round_btn.setObjectName("SecondaryButton")

        self.next_round_btn.style().unpolish(self.next_round_btn)
        self.next_round_btn.style().polish(self.next_round_btn)

    def set_swiss_mode(self, enabled: bool):
        """Active/désactive le mode Swiss (cache 'Round varié')."""
        if enabled:
            self.shuffle_round_btn.setVisible(False)
            self.shuffle_round_btn.setEnabled(False)
            self.repetition_label.setVisible(False)
        self.next_round_btn.setText("⏭  Round suivante")

    def set_edit_pairings_visible(self, visible: bool):
        """Affiche ou cache le bouton de modification des pairings."""
        self.edit_pairings_btn.setVisible(visible)

    def show_repetition_warning(self, rate: float):
        self.shuffle_round_btn.setEnabled(True)
        self.shuffle_round_btn.setVisible(True)
        self.repetition_label.setText(f"⚠️  {rate:.0f}% de répétitions dans le prochain round")
        self.repetition_label.setVisible(True)

    def hide_repetition_warning(self):
        self.shuffle_round_btn.setEnabled(False)
        self.shuffle_round_btn.setVisible(False)
        self.repetition_label.setVisible(False)

    def show_archive_button(self):
        self.archive_btn.setVisible(True)
        self.export_pdf_btn.setVisible(True)

    def hide_archive_button(self):
        self.archive_btn.setVisible(False)
        self.export_pdf_btn.setVisible(False)

    def show_bracket_launch_button(self):
        """Affiche le bouton 'Lancer le bracket' après le dernier round Swiss."""
        self.launch_bracket_btn.setVisible(True)

    def hide_bracket_launch_button(self):
        self.launch_bracket_btn.setVisible(False)

    def set_bracket_mode(self):
        """Passe en mode bracket : cache les contrôles Swiss inutiles."""
        self.launch_bracket_btn.setVisible(False)
        self.shuffle_round_btn.setVisible(False)
        self.edit_pairings_btn.setVisible(False)
        self.repetition_label.setVisible(False)
        self.next_round_btn.setText("⏭  Phase suivante")
        self.next_round_btn.setObjectName("SecondaryButton")
        self.next_round_btn.style().unpolish(self.next_round_btn)
        self.next_round_btn.style().polish(self.next_round_btn)
