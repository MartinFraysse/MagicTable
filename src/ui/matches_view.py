from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout

class MatchesView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("⚔️ Matchs (à venir)"))
