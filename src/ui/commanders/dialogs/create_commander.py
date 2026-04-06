from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QCheckBox,
    QPushButton, QFrame,
)

from core.commander import Commander


_COLORS = [
    ("W", "☀️", "#f5f5dc", "#333333"),
    ("U", "💧", "#4a90d9", "#ffffff"),
    ("B", "💀", "#2a2a2a", "#ffffff"),
    ("R", "🔥", "#d9534f", "#ffffff"),
    ("G", "🌿", "#2e7d32", "#ffffff"),
]

_FORMAT_OPTIONS = [
    ("both",      "Les deux"),
    ("commander", "👑 Commander Multi"),
    ("duel",      "⚔️ Duel Commander"),
]


class CreateCommanderDialog(QDialog):
    """Dialog pour créer ou éditer un commandant."""

    def __init__(
        self,
        parent=None,
        commander: Commander | None = None,
        existing_names: list[str] | None = None,
    ):
        super().__init__(parent)

        self._commander = commander
        self._is_edit = commander is not None
        self._existing_names = [n.lower() for n in (existing_names or [])]
        if self._is_edit and commander:
            self._existing_names = [n for n in self._existing_names if n != commander.name.lower()]

        self.setWindowTitle("Modifier le commandant" if self._is_edit else "Nouveau commandant")
        self.setModal(True)
        self.setFixedSize(400, 290)
        self.setObjectName("CreateCommanderDialog")

        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        # Titre
        title = QLabel("✏️ Modifier le commandant" if self._is_edit else "➕ Nouveau commandant")
        title.setObjectName("DialogTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Formulaire
        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignRight)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nom du commandant")
        self.name_input.setObjectName("DialogInput")
        self.name_input.textChanged.connect(self._clear_error)
        form.addRow("Nom *", self.name_input)

        self.error_label = QLabel("")
        self.error_label.setObjectName("ErrorLabel")
        self.error_label.hide()
        form.addRow("", self.error_label)

        self.format_combo = QComboBox()
        self.format_combo.setObjectName("DialogInput")
        for key, label in _FORMAT_OPTIONS:
            self.format_combo.addItem(label, key)
        form.addRow("Format", self.format_combo)

        layout.addLayout(form)

        # Couleurs
        colors_row = QHBoxLayout()
        colors_row.setSpacing(6)
        colors_label = QLabel("Couleurs")
        colors_label.setObjectName("FormLabel")
        colors_label.setFixedWidth(80)
        colors_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        colors_row.addWidget(colors_label)

        self._color_checks: dict[str, QCheckBox] = {}
        for letter, emoji, bg, fg in _COLORS:
            cb = QCheckBox(f" {emoji} {letter}")
            cb.setObjectName("ColorCheckBox")
            self._color_checks[letter] = cb
            colors_row.addWidget(cb)

        colors_row.addStretch()
        layout.addLayout(colors_row)

        layout.addStretch()

        # Boutons
        buttons = QHBoxLayout()
        buttons.setSpacing(12)

        cancel_btn = QPushButton("Annuler")
        cancel_btn.setObjectName("CancelButton")
        cancel_btn.clicked.connect(self.reject)

        self.save_btn = QPushButton("Enregistrer" if self._is_edit else "Créer")
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.clicked.connect(self._validate_and_accept)

        buttons.addStretch()
        buttons.addWidget(cancel_btn)
        buttons.addWidget(self.save_btn)
        layout.addLayout(buttons)

        self.name_input.setFocus()

    def _load_data(self):
        if not self._commander:
            return
        self.name_input.setText(self._commander.name)
        idx = self.format_combo.findData(self._commander.format)
        if idx >= 0:
            self.format_combo.setCurrentIndex(idx)
        for letter, cb in self._color_checks.items():
            cb.setChecked(letter in self._commander.colors.upper())

    def _clear_error(self):
        self.error_label.hide()
        self.name_input.setProperty("error", False)
        self.name_input.style().unpolish(self.name_input)
        self.name_input.style().polish(self.name_input)

    def _show_error(self, message: str):
        self.error_label.setText(message)
        self.error_label.show()
        self.name_input.setProperty("error", True)
        self.name_input.style().unpolish(self.name_input)
        self.name_input.style().polish(self.name_input)
        self.name_input.setFocus()

    def _validate_and_accept(self):
        name = self.name_input.text().strip()
        if not name:
            self._show_error("Le nom est requis")
            return
        if name.lower() in self._existing_names:
            self._show_error("Ce commandant existe déjà")
            return
        self.accept()

    def get_data(self) -> dict:
        colors = "".join(l for l, cb in self._color_checks.items() if cb.isChecked())
        return {
            "name":   self.name_input.text().strip(),
            "colors": colors,
            "format": self.format_combo.currentData(),
        }

    def apply_changes(self):
        if not self._commander:
            return
        data = self.get_data()
        self._commander.name   = data["name"]
        self._commander.colors = data["colors"]
        self._commander.format = data["format"]
