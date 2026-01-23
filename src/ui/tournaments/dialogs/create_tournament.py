from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton,
    QLabel, QComboBox, QSpinBox, QAbstractSpinBox,
    QStyledItemDelegate,
)
from PySide6.QtCore import Qt, QSize
from core.tournament import Tournament




class CreateTournamentDialog(QDialog):
    """
    Dialog de création / édition de tournoi.
    """

    def __init__(self, parent=None, tournament: Tournament | None = None):
        super().__init__(parent)

        self._edit_mode = tournament is not None
        self._tournament = tournament

        self.setWindowTitle("Tournoi")
        self.setModal(True)
        self.setFixedSize(400, 540)
        self.setObjectName("CreateTournamentDialog")

        root = QVBoxLayout(self)
        root.setSpacing(22)
        root.setContentsMargins(28, 26, 28, 26)

        # =====================
        # Title
        # =====================
        title = QLabel(
            "✏️ Modifier le tournoi" if self._edit_mode else "🏆 Nouveau tournoi"
        )
        title.setObjectName("DialogTitle")
        title.setAlignment(Qt.AlignCenter)
        root.addWidget(title)

        # =====================
        # Name
        # =====================
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nom du tournoi")
        self.name_input.setMinimumHeight(42)
        self.name_input.textChanged.connect(self._update_state)
        root.addWidget(self.name_input)

        # =====================
        # Format (ComboBox)
        # =====================
        self.format_input = QComboBox()
        self.format_input.setObjectName("FormatComboBox")
        self.format_input.setMinimumHeight(42)
        self.format_input.setEditable(False)

        self.format_input.setItemDelegate(ComboBoxItemDelegate())

        self.format_input.addItem("🎴 Format du tournoi")
        
        # Formats prédéfinis
        self.format_input.addItems([
            "👑 Commander",
            "⚔️ Duel Commander",
            "🃏 Draft",
            "🏆 AP",
            "⚡ Pokemon",
            "🔥 Rise",
        ])

        self.format_input.currentIndexChanged.connect(self._update_state)
        root.addWidget(self.format_input)

        # =====================
        # Date
        # =====================
        self.date_input = QLineEdit()
        self.date_input.setInputMask("00/00/0000;_")
        self.date_input.setAlignment(Qt.AlignCenter)
        self.date_input.setMinimumHeight(42)
        self.date_input.textChanged.connect(self._update_state)
        root.addWidget(self.date_input)

        # =====================
        # Nombre de rounds
        # =====================
        rounds_layout = QHBoxLayout()
        rounds_layout.setSpacing(12)

        rounds_label = QLabel("Nombre de rounds")
        rounds_layout.addWidget(rounds_label)

        rounds_layout.addStretch()

        self.rounds_input = QSpinBox()
        self.rounds_input.setObjectName("RoundsSpinBox")
        self.rounds_input.setButtonSymbols(QAbstractSpinBox.PlusMinus)
        self.rounds_input.setMinimum(1)
        self.rounds_input.setMaximum(10)
        self.rounds_input.setValue(3)
        self.rounds_input.setFixedSize(120, 42)
        self.rounds_input.setAlignment(Qt.AlignCenter)
        self.rounds_input.valueChanged.connect(self._update_state)
        rounds_layout.addWidget(self.rounds_input)

        root.addLayout(rounds_layout)

        # =====================
        # Preview
        # =====================
        self.preview = QLabel()
        self.preview.setObjectName("TournamentPreview")
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setWordWrap(True)
        self.preview.setMinimumHeight(70)
        root.addWidget(self.preview)

        root.addStretch()

        # =====================
        # Actions
        # =====================
        actions = QHBoxLayout()
        actions.addStretch()

        cancel_btn = QPushButton("Annuler")
        cancel_btn.setObjectName("CancelButton")
        cancel_btn.clicked.connect(self.reject)

        self.confirm_btn = QPushButton(
            "Modifier" if self._edit_mode else "Créer"
        )
        self.confirm_btn.setObjectName("CreateButton")
        self.confirm_btn.setEnabled(False)

        # 🔑 CLÉ DU COMPORTEMENT ENTER
        self.confirm_btn.setDefault(True)
        self.confirm_btn.setAutoDefault(True)

        self.confirm_btn.clicked.connect(self._validate)


        actions.addWidget(cancel_btn)
        actions.addWidget(self.confirm_btn)

        root.addLayout(actions)

        if self._edit_mode:
            self._load_tournament()

        self._update_state()

    # =====================
    # Internal logic
    # =====================

    def _load_tournament(self):
        t = self._tournament
        self.name_input.setText(t.name)
        self.format_input.setCurrentText(t.format)
        self.date_input.setText(t.date)
        self.rounds_input.setValue(t.max_rounds)

    def _update_state(self):
        name = self.name_input.text().strip()
        date = self.date_input.text()
        rounds = self.rounds_input.value()

        format_valid = self.format_input.currentIndex() > 0
        valid = bool(name and format_valid and "_" not in date)

        self.confirm_btn.setEnabled(valid)

        fmt = self.format_input.currentText() if format_valid else "Format"
        self.preview.setText(
            f"<b>{name or 'Nom du tournoi'}</b><br>"
            f"{fmt} • {date or 'Date'} • {rounds} rounds"
        )

    def _validate(self):
        self.accept()

    # =====================
    # Public API
    # =====================
    def apply_changes(self):
        if not self._tournament:
            return

        self._tournament.update(
            name=self.name_input.text(),
            format=self.format_input.currentText(),
            date=self.date_input.text(),
            max_rounds=self.rounds_input.value(),
        )

    def get_max_rounds(self) -> int:
        return self.rounds_input.value()


class ComboBoxItemDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(42)  # 👈 hauteur réelle des items
        return size
