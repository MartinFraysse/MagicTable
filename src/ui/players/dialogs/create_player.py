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
)

from core.regular_player import RegularPlayer


class CreatePlayerDialog(QDialog):
    """Dialog pour créer ou éditer un joueur régulier."""

    def __init__(
        self,
        parent=None,
        player: RegularPlayer | None = None,
        existing_pseudos: list[str] | None = None,
    ):
        super().__init__(parent)

        self._player = player
        self._is_edit = player is not None
        self._existing_pseudos = [p.lower() for p in (existing_pseudos or [])]

        # En mode édition, retirer le pseudo actuel de la liste
        if self._is_edit and player:
            self._existing_pseudos = [
                p for p in self._existing_pseudos if p != player.pseudo.lower()
            ]

        self.setWindowTitle("Modifier le joueur" if self._is_edit else "Nouveau joueur")
        self.setModal(True)
        self.setFixedSize(380, 360)
        self.setObjectName("CreatePlayerDialog")

        # Éviter les coins blancs
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor("#0f241d"))
        self.setPalette(palette)

        self._build_ui()
        self._load_data()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 16, 20, 16)

        # Titre
        title = QLabel("✏️ Modifier le joueur" if self._is_edit else "➕ Nouveau joueur")
        title.setObjectName("DialogTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Formulaire
        form = QFormLayout()
        form.setSpacing(8)

        self.pseudo_input = QLineEdit()
        self.pseudo_input.setPlaceholderText("Pseudo du joueur")
        self.pseudo_input.setObjectName("DialogInput")
        self.pseudo_input.textChanged.connect(self._clear_error)
        self.pseudo_input.returnPressed.connect(self._validate_and_accept)
        form.addRow("Pseudo *", self.pseudo_input)

        # Label d'erreur
        self.error_label = QLabel("")
        self.error_label.setObjectName("ErrorLabel")
        self.error_label.hide()
        form.addRow("", self.error_label)

        self.full_name_input = QLineEdit()
        self.full_name_input.setPlaceholderText("Nom complet (optionnel)")
        self.full_name_input.setObjectName("DialogInput")
        self.full_name_input.returnPressed.connect(self._validate_and_accept)
        form.addRow("Nom complet", self.full_name_input)

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("Optionnel - max 10 chiffres")
        self.phone_input.setObjectName("DialogInput")
        self.phone_input.textChanged.connect(self._format_phone_input)
        self.phone_input.returnPressed.connect(self._validate_and_accept)
        form.addRow("Téléphone", self.phone_input)

        self.discord_input = QLineEdit()
        self.discord_input.setPlaceholderText("ID Discord (ex: 123456789012345678)")
        self.discord_input.setObjectName("DialogInput")
        self.discord_input.textChanged.connect(self._format_discord_input)
        self.discord_input.returnPressed.connect(self._validate_and_accept)
        form.addRow("Discord ID", self.discord_input)

        layout.addLayout(form)

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

        # Focus sur le pseudo
        self.pseudo_input.setFocus()

    def _load_data(self):
        """Charge les données du joueur si édition."""
        if not self._player:
            return

        self.pseudo_input.setText(self._player.pseudo)
        self.full_name_input.setText(self._player.full_name)
        self.phone_input.setText(self._player.phone)
        self.discord_input.setText(self._player.discord_id)

    def _clear_error(self):
        """Efface l'erreur quand l'utilisateur tape."""
        self.error_label.hide()
        self.pseudo_input.setProperty("error", False)
        self.pseudo_input.style().unpolish(self.pseudo_input)
        self.pseudo_input.style().polish(self.pseudo_input)

    def _format_discord_input(self, text: str):
        """N'autorise que les chiffres dans le champ Discord ID."""
        digits = ''.join(c for c in text if c.isdigit())
        if digits != text:
            self.discord_input.blockSignals(True)
            self.discord_input.setText(digits)
            self.discord_input.blockSignals(False)

    def _format_phone_input(self, text: str):
        """Formate le numéro de téléphone en temps réel (max 10 chiffres)."""
        # Extraire seulement les chiffres
        digits = ''.join(c for c in text if c.isdigit())

        # Limiter à 10 chiffres
        digits = digits[:10]

        # Formater en xx xx xx xx xx
        formatted = ' '.join(digits[i:i+2] for i in range(0, len(digits), 2))

        # Mettre à jour seulement si différent (évite boucle infinie)
        if formatted != text:
            self.phone_input.blockSignals(True)
            cursor_pos = self.phone_input.cursorPosition()
            self.phone_input.setText(formatted)
            # Ajuster la position du curseur
            new_pos = min(cursor_pos + (len(formatted) - len(text)), len(formatted))
            self.phone_input.setCursorPosition(max(0, new_pos))
            self.phone_input.blockSignals(False)

    def _show_error(self, message: str):
        """Affiche une erreur."""
        self.error_label.setText(message)
        self.error_label.show()
        self.pseudo_input.setProperty("error", True)
        self.pseudo_input.style().unpolish(self.pseudo_input)
        self.pseudo_input.style().polish(self.pseudo_input)
        self.pseudo_input.setFocus()

    def _validate_and_accept(self):
        """Valide le formulaire et accepte le dialog."""
        pseudo = self.pseudo_input.text().strip()

        if not pseudo:
            self._show_error("Le pseudo est requis")
            return

        if pseudo.lower() in self._existing_pseudos:
            self._show_error("Ce pseudo existe déjà")
            return

        self.accept()

    def get_data(self) -> dict:
        """Retourne les données du formulaire."""
        return {
            "pseudo": self.pseudo_input.text().strip(),
            "full_name": self.full_name_input.text().strip(),
            "phone": self.phone_input.text().strip(),
            "discord_id": self.discord_input.text().strip(),
        }

    def apply_changes(self):
        """Applique les changements au joueur existant."""
        if not self._player:
            return

        data = self.get_data()
        self._player.pseudo = data["pseudo"]
        self._player.full_name = data["full_name"]
        self._player.phone = data["phone"]
        self._player.discord_id = data["discord_id"]
