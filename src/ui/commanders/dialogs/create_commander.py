from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLabel, QLineEdit, QButtonGroup,
    QPushButton, QWidget,
)

from core.commander import Commander


_COLORS = [
    ("W", "☀️  W"),
    ("U", "💧  U"),
    ("B", "💀  B"),
    ("R", "🔥  R"),
    ("G", "🌿  G"),
]

_FORMAT_OPTIONS = [
    ("duel",      "⚔️  Duel"),
    ("commander", "👑  Multi"),
    ("both",      "Les deux"),
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
        self.setFixedSize(460, 310)
        self.setObjectName("CreateCommanderDialog")

        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 18, 24, 18)

        # Titre
        title = QLabel("✏️ Modifier le commandant" if self._is_edit else "➕ Nouveau commandant")
        title.setObjectName("DialogTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Formulaire
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nom du commandant")
        self.name_input.setObjectName("DialogInput")
        self.name_input.textChanged.connect(self._clear_error)
        self.name_input.returnPressed.connect(self._validate_and_accept)
        form.addRow("Nom *", self.name_input)

        self.error_label = QLabel("")
        self.error_label.setObjectName("ErrorLabel")
        self.error_label.hide()
        form.addRow("", self.error_label)

        # Format — 3 boutons exclusifs
        fmt_widget = QWidget()
        fmt_layout = QHBoxLayout(fmt_widget)
        fmt_layout.setContentsMargins(0, 0, 0, 0)
        fmt_layout.setSpacing(8)

        self._format_group = QButtonGroup(self)
        self._format_group.setExclusive(True)
        self._format_btns: dict[str, QPushButton] = {}

        for key, label in _FORMAT_OPTIONS:
            btn = QPushButton(label)
            btn.setObjectName("FormatButton")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            self._format_group.addButton(btn)
            self._format_btns[key] = btn
            fmt_layout.addWidget(btn)

        fmt_layout.addStretch()
        form.addRow("Format", fmt_widget)

        # Couleurs — 5 boutons carrés MTG
        color_widget = QWidget()
        color_layout = QHBoxLayout(color_widget)
        color_layout.setContentsMargins(0, 0, 0, 0)
        color_layout.setSpacing(8)

        self._color_btns: dict[str, QPushButton] = {}
        for letter, label in _COLORS:
            btn = QPushButton(label)
            btn.setObjectName(f"ColorBtn_{letter}")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedSize(62, 52)
            self._color_btns[letter] = btn
            color_layout.addWidget(btn)

        color_layout.addStretch()
        form.addRow("Couleurs", color_widget)

        layout.addLayout(form)
        layout.addStretch()

        # Boutons d'action
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

        # Format par défaut : "Les deux"
        self._format_btns["both"].setChecked(True)

    def _load_data(self):
        if not self._commander:
            return
        self.name_input.setText(self._commander.name)
        fmt = self._commander.format
        if fmt in self._format_btns:
            self._format_btns[fmt].setChecked(True)
        for letter, btn in self._color_btns.items():
            btn.setChecked(letter in self._commander.colors.upper())

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
        fmt = "both"
        for key, btn in self._format_btns.items():
            if btn.isChecked():
                fmt = key
                break
        colors = "".join(l for l, btn in self._color_btns.items() if btn.isChecked())
        return {
            "name":   self.name_input.text().strip(),
            "colors": colors,
            "format": fmt,
        }

    def apply_changes(self):
        if not self._commander:
            return
        data = self.get_data()
        self._commander.name   = data["name"]
        self._commander.colors = data["colors"]
        self._commander.format = data["format"]
