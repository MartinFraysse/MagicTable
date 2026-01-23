from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton
from PySide6.QtCore import Signal


class DashboardRoundControlsView(QWidget):
    """
    Zone de contrôle de la round :
    - ▶️ Lancer la round (one-shot)
    - ⏭ Round suivant
    """

    start_round_requested = Signal()
    next_round_requested = Signal()

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

        layout.addWidget(self.start_round_btn)
        layout.addWidget(self.next_round_btn)

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

