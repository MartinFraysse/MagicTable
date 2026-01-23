from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox,
    QStyledItemDelegate,
)
from PySide6.QtCore import Qt

from core.table import Table
from core.player import Player


class EditTableResultsDialog(QDialog):
    """
    Dialog de définition des résultats d'une table.
    """

    def __init__(self, parent=None, table: Table | None = None):
        super().__init__(parent)

        if table is None:
            raise ValueError("Table is required")

        self.table = table

        self.setWindowTitle(f"Résultats — Table {table.number}")
        self.setModal(True)

        # Taille adaptative selon le nombre de joueurs
        if len(table.players) >= 3:
            self.setFixedSize(360, 360)
        else:
            self.setFixedSize(360, 260)

        self.setObjectName("EditTableResultsDialog")

        # =====================
        # Layout
        # =====================
        root = QVBoxLayout(self)
        root.setSpacing(8)
        root.setContentsMargins(28, 26, 28, 26)

        # =====================
        # Title
        # =====================
        title = QLabel("🏁 Définir les résultats")
        title.setObjectName("DialogTitle")
        title.setAlignment(Qt.AlignCenter)
        root.addWidget(title)
        root.addSpacing(18)

        # =====================
        # Winner
        # =====================
        winner_label = QLabel("Vainqueur")
        root.addWidget(winner_label)

        self.winner_combo = self._build_player_combo(
            placeholder="🏆 Sélectionner le vainqueur"
        )
        root.addWidget(self.winner_combo)
        root.addSpacing(18)

        # =====================
        # Second (multi / commander)
        # =====================
        self.second_combo = None
        if len(table.players) >= 3:
            second_label = QLabel("Second")
            root.addWidget(second_label)

            self.second_combo = self._build_player_combo(
                placeholder="🥈 Sélectionner le second"
            )
            root.addWidget(self.second_combo)
            root.addSpacing(18)

        root.addStretch()

        # =====================
        # Actions
        # =====================
        actions = QHBoxLayout()
        actions.addStretch()

        cancel_btn = QPushButton("Annuler")
        cancel_btn.setObjectName("CancelButton")
        cancel_btn.clicked.connect(self.reject)

        self.confirm_btn = QPushButton("Valider")
        self.confirm_btn.setObjectName("CreateButton")
        self.confirm_btn.setDefault(True)
        self.confirm_btn.setAutoDefault(True)
        self.confirm_btn.setEnabled(False)  # ❌ désactivé par défaut
        self.confirm_btn.clicked.connect(self.accept)

        actions.addWidget(cancel_btn)
        actions.addWidget(self.confirm_btn)
        root.addLayout(actions)

        # =====================
        # Signals
        # =====================
        self.winner_combo.currentIndexChanged.connect(
            self._on_winner_changed
        )
        self.winner_combo.currentIndexChanged.connect(
            self._update_validation_state
        )

        if self.second_combo:
            self.second_combo.currentIndexChanged.connect(
                self._update_validation_state
            )

    # ======================================================
    # UI helpers
    # ======================================================
    def _build_player_combo(self, placeholder: str) -> QComboBox:
        combo = QComboBox()
        combo.setObjectName("FormatComboBox")
        combo.setMinimumHeight(42)
        combo.setEditable(False)
        combo.setItemDelegate(ComboBoxItemDelegate())

        # Placeholder (index 0)
        combo.addItem(placeholder, None)

        # Joueurs
        for player in self.table.players:
            combo.addItem(player.name, player)

        # Cacher le placeholder dans la liste déroulante
        combo.view().setRowHidden(0, True)

        return combo

    # ======================================================
    # Validation
    # ======================================================
    def _update_validation_state(self):
        """
        Active le bouton Valider uniquement si les sélections sont valides.
        """
        winner_ok = self.winner_combo.currentIndex() > 0

        if self.second_combo:
            second_ok = self.second_combo.currentIndex() > 0
            valid = winner_ok and second_ok
        else:
            valid = winner_ok

        self.confirm_btn.setEnabled(valid)

    # ======================================================
    # Résultats
    # ======================================================
    def results(self) -> dict[int, int]:
        """
        player_id -> position
        1 = vainqueur
        2 = second (si défini)
        3 = tous les autres
        """
        results: dict[int, int] = {}

        winner: Player | None = self.winner_combo.currentData()
        second: Player | None = (
            self.second_combo.currentData() if self.second_combo else None
        )

        if winner:
            results[winner.id] = 1

        if second and (not winner or second.id != winner.id):
            results[second.id] = 2

        for player in self.table.players:
            if player.id not in results:
                results[player.id] = 3

        return results

    # ======================================================
    # Synchronisation winner / second
    # ======================================================
    def _on_winner_changed(self):
        if not self.second_combo:
            return

        winner: Player | None = self.winner_combo.currentData()

        self.second_combo.blockSignals(True)
        self.second_combo.clear()

        # Placeholder
        self.second_combo.addItem("🥈 Sélectionner le second", None)

        for player in self.table.players:
            if not winner or player.id != winner.id:
                self.second_combo.addItem(player.name, player)

        # Recacher le placeholder
        self.second_combo.view().setRowHidden(0, True)

        self.second_combo.setCurrentIndex(0)
        self.second_combo.blockSignals(False)


class ComboBoxItemDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(42)
        return size
