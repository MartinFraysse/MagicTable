from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QSizePolicy


class PlayerMatchesPopup(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent, Qt.ToolTip)

        self.setObjectName("PlayerMatchesPopup")
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)

        self.setSizePolicy(
            QSizePolicy.Minimum,
            QSizePolicy.Minimum
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(12, 10, 12, 10)

        self.title = QLabel("👤 Joueur")
        self.title.setObjectName("PopupTitle")

        self.content = QLabel("")
        self.content.setObjectName("PopupContent")
        self.content.setTextFormat(Qt.RichText)

        layout.addWidget(self.title)
        layout.addWidget(self.content)

        self.hide()

    def set_player(self, name: str, matches: list):
        self.title.setText(f"👤 {name}")

        lines = []
        for m in matches:
            lines.append(
                f"<b>Round {m['round']}</b> — Table {m['table']}<br>"
                f"Résultat : <b>{m['position']}</b>"
            )

        self.content.setText("<hr>".join(lines))

        self.adjustSize()  # 🔑 CRUCIAL

