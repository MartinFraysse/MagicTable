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

    def set_player(self, name: str, matches: list, robustness: int = 0):
        self.title.setText(f"👤 {name}")

        lines = []
        for m in matches:
            points = m.get('points', 0)
            lines.append(
                f"<b>Round {m['round']}</b> — Table {m['table']}<br>"
                f"{m['position']} → <span style='color: #3fd27d;'>+{points} pts</span>"
            )

        content_text = "<hr>".join(lines) if lines else "Aucun résultat"

        # Ajouter la robustesse
        content_text += f"<hr><b>Robustesse:</b> <span style='color: #f1c40f;'>{robustness}</span>"

        self.content.setText(content_text)

        self.adjustSize()  # 🔑 CRUCIAL

