from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFormLayout,
    QCheckBox,
    QFrame,
)

from core.commander import Commander, MTG_COLORS, COLOR_LABELS, COLOR_SYMBOLS, COLOR_HEX


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
            self._existing_names = [
                n for n in self._existing_names if n != commander.name.lower()
            ]

        self.setWindowTitle("Modifier le commandant" if self._is_edit else "Nouveau commandant")
        self.setModal(True)
        self.setFixedSize(420, 320)
        self.setObjectName("CreatePlayerDialog")

        self.setAttribute(Qt.WA_TranslucentBackground, False)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor("#0f241d"))
        self.setPalette(palette)

        self._color_checkboxes: dict[str, QPushButton] = {}

        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 20, 24, 20)

        # Titre
        title = QLabel("✏️ Modifier le commandant" if self._is_edit else "➕ Nouveau commandant")
        title.setObjectName("DialogTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Formulaire nom
        form = QFormLayout()
        form.setSpacing(8)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ex : Atraxa, Praetors' Voice")
        self.name_input.setObjectName("DialogInput")
        self.name_input.textChanged.connect(self._clear_error)
        self.name_input.returnPressed.connect(self._validate_and_accept)
        form.addRow("Nom *", self.name_input)

        self.error_label = QLabel("")
        self.error_label.setObjectName("ErrorLabel")
        self.error_label.hide()
        form.addRow("", self.error_label)

        layout.addLayout(form)

        # Section couleurs
        colors_label = QLabel("Couleurs")
        colors_label.setObjectName("StatsLabel")
        layout.addWidget(colors_label)

        colors_row = QHBoxLayout()
        colors_row.setSpacing(10)
        colors_row.setAlignment(Qt.AlignCenter)

        for code in MTG_COLORS:
            btn = QPushButton(COLOR_SYMBOLS[code])
            btn.setCheckable(True)
            btn.setObjectName("ColorToggleButton")
            btn.setFixedSize(38, 38)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(COLOR_LABELS[code])
            btn.setProperty("colorCode", code)
            btn.setStyleSheet(self._get_color_btn_style(code, False))
            btn.toggled.connect(lambda checked, b=btn, c=code: self._on_color_toggled(b, c, checked))

            self._color_checkboxes[code] = btn
            colors_row.addWidget(btn)

        layout.addLayout(colors_row)

        # Aperçu incolore
        self.colorless_label = QLabel("Incolore")
        self.colorless_label.setObjectName("StatsLabel")
        self.colorless_label.hide()
        layout.addWidget(self.colorless_label)

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

    def _get_color_btn_style(self, code: str, checked: bool) -> str:
        hex_color = COLOR_HEX[code]
        size = "min-width:38px;max-width:38px;min-height:38px;max-height:38px;padding:0px;"
        if checked:
            text_color = "#1a1a1a" if code == "W" else "#ffffff"
            return (
                f"QPushButton {{"
                f"  {size}"
                f"  background-color: {hex_color};"
                f"  color: {text_color};"
                f"  border: 3px solid rgba(255,255,255,0.85);"
                f"  border-radius: 19px;"
                f"  font-size: 18px;"
                f"}}"
                f"QPushButton:hover {{"
                f"  border: 3px solid rgba(255,255,255,1);"
                f"}}"
            )
        else:
            return (
                f"QPushButton {{"
                f"  {size}"
                f"  background-color: #132f26;"
                f"  color: {hex_color};"
                f"  border: 2px solid {hex_color}99;"
                f"  border-radius: 19px;"
                f"  font-size: 18px;"
                f"}}"
                f"QPushButton:hover {{"
                f"  background-color: {hex_color}22;"
                f"  border: 2px solid {hex_color};"
                f"}}"
            )

    def _on_color_toggled(self, btn: QPushButton, code: str, checked: bool):
        btn.setStyleSheet(self._get_color_btn_style(code, checked))

        any_checked = any(b.isChecked() for b in self._color_checkboxes.values())
        self.colorless_label.setVisible(not any_checked)

    def _load_data(self):
        if not self._commander:
            return
        self.name_input.setText(self._commander.name)
        for code, btn in self._color_checkboxes.items():
            btn.setChecked(code in self._commander.colors)

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
        colors = [code for code, btn in self._color_checkboxes.items() if btn.isChecked()]
        return {
            "name": self.name_input.text().strip(),
            "colors": colors,
        }

    def apply_changes(self):
        if not self._commander:
            return
        data = self.get_data()
        self._commander.name = data["name"]
        self._commander.colors = data["colors"]
