from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
)
from PySide6.QtCore import Qt


class EditPlayerDialog(QDialog):
    def __init__(self, parent=None, name=""):
        super().__init__(parent)

        self.setWindowTitle("Modifier le joueur")
        self.setFixedSize(280, 180)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        label = QLabel("Nom du joueur :")
        layout.addWidget(label)

        self.input = QLineEdit()
        self.input.setText(name)
        self.input.selectAll()
        layout.addWidget(self.input)

        buttons = QHBoxLayout()
        buttons.addStretch()

        cancel_btn = QPushButton("Annulé")
        cancel_btn.clicked.connect(self.reject)

        ok_btn = QPushButton("Validé")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self.accept)

        buttons.addWidget(cancel_btn)
        buttons.addWidget(ok_btn)

        layout.addLayout(buttons)

    def value(self):
        return self.input.text().strip()
