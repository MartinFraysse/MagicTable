from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox,
    QStyledItemDelegate, QSpinBox,
)
from PySide6.QtCore import Qt

from core.table import Table
from core.player import Player

# Scores valides (games p1, games p2) — BO1 et BO3
_VALID_SCORES = {(1, 0), (0, 1), (2, 0), (2, 1), (1, 1), (1, 2), (0, 2)}


class EditTableResultsDialog(QDialog):
    """
    Dialog de définition des résultats d'une table.

    - 1v1 (2 joueurs) : saisie du score BO3 via deux champs numériques
    - Commander (3-4 joueurs) : choix du vainqueur et second
    """

    def __init__(self, parent=None, table: Table | None = None):
        super().__init__(parent)

        if table is None:
            raise ValueError("Table is required")

        self.table = table
        self._is_1v1 = len(table.players) == 2

        # Spinboxes BO3 (initialisées dans _build_bo3_ui)
        self._spin_p1: QSpinBox | None = None
        self._spin_p2: QSpinBox | None = None
        self._bo3_status_lbl: QLabel | None = None

        # Combos Commander (initialisées dans _build_commander_ui)
        self.winner_combo: QComboBox | None = None
        self.second_combo: QComboBox | None = None

        self.setWindowTitle(f"Résultats — Table {table.number}")
        self.setModal(True)
        self.setObjectName("EditTableResultsDialog")

        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(28, 26, 28, 26)

        # Titre
        title = QLabel("🏁 Résultat du match")
        title.setObjectName("DialogTitle")
        title.setAlignment(Qt.AlignCenter)
        root.addWidget(title)
        root.addSpacing(16)

        if self._is_1v1:
            self._build_bo3_ui(root)
            self.setFixedSize(400, 340)
        else:
            self._build_commander_ui(root)
            h = 360 if len(table.players) >= 3 else 260
            self.setFixedSize(360, h)

        root.addStretch()

        # Boutons d'action
        actions = QHBoxLayout()
        actions.addStretch()

        cancel_btn = QPushButton("Annuler")
        cancel_btn.setObjectName("CancelButton")
        cancel_btn.clicked.connect(self.reject)

        self.confirm_btn = QPushButton("Valider")
        self.confirm_btn.setObjectName("CreateButton")
        self.confirm_btn.setDefault(True)
        self.confirm_btn.setAutoDefault(True)
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.clicked.connect(self.accept)

        actions.addWidget(cancel_btn)
        actions.addWidget(self.confirm_btn)
        root.addLayout(actions)

    # ======================================================
    # UI BO3 — deux lignes nom + spinbox
    # ======================================================
    def _build_bo3_ui(self, root: QVBoxLayout):
        p1, p2 = self.table.players

        for player, attr in [(p1, "_spin_p1"), (p2, "_spin_p2")]:
            row = QHBoxLayout()
            row.setSpacing(16)

            lbl = QLabel(player.name)
            lbl.setObjectName("BO3PlayerName")

            spin = QSpinBox()
            spin.setObjectName("BO3SpinBox")
            spin.setRange(0, 3)
            spin.setValue(0)
            spin.setMinimumHeight(46)
            spin.setMinimumWidth(90)
            spin.setAlignment(Qt.AlignCenter)

            setattr(self, attr, spin)
            row.addWidget(lbl, 1)
            row.addWidget(spin)
            root.addLayout(row)

        # Label d'état (résultat en cours / invalide)
        self._bo3_status_lbl = QLabel("")
        self._bo3_status_lbl.setObjectName("BO3StatusLabel")
        self._bo3_status_lbl.setAlignment(Qt.AlignCenter)
        root.addSpacing(4)
        root.addWidget(self._bo3_status_lbl)

        self._spin_p1.valueChanged.connect(self._on_score_changed)
        self._spin_p2.valueChanged.connect(self._on_score_changed)

    def _on_score_changed(self):
        g1 = self._spin_p1.value()
        g2 = self._spin_p2.value()
        p1, p2 = self.table.players
        valid = (g1, g2) in _VALID_SCORES

        if g1 == 0 and g2 == 0:
            self._bo3_status_lbl.setText("")
            self._bo3_status_lbl.setProperty("state", "")
        elif valid:
            if g1 > g2:
                self._bo3_status_lbl.setText(f"🏆 {p1.name} gagne {g1}‑{g2}")
            elif g2 > g1:
                self._bo3_status_lbl.setText(f"🏆 {p2.name} gagne {g2}‑{g1}")
            else:
                self._bo3_status_lbl.setText(f"⚖️ Match nul {g1}‑{g2}")
            self._bo3_status_lbl.setProperty("state", "valid")
        else:
            self._bo3_status_lbl.setText("Score invalide — ex: 1‑0, 2‑0, 2‑1, 1‑1")
            self._bo3_status_lbl.setProperty("state", "invalid")

        # Forcer le rechargement du style (propriété dynamique)
        self._bo3_status_lbl.style().unpolish(self._bo3_status_lbl)
        self._bo3_status_lbl.style().polish(self._bo3_status_lbl)

        self._update_validation_state()

    # ======================================================
    # UI Commander — vainqueur + second
    # ======================================================
    def _build_commander_ui(self, root: QVBoxLayout):
        winner_label = QLabel("Vainqueur")
        root.addWidget(winner_label)

        self.winner_combo = self._build_player_combo("🏆 Sélectionner le vainqueur")
        root.addWidget(self.winner_combo)
        root.addSpacing(18)

        if len(self.table.players) >= 3:
            second_label = QLabel("Second")
            root.addWidget(second_label)

            self.second_combo = self._build_player_combo("🥈 Sélectionner le second")
            root.addWidget(self.second_combo)
            root.addSpacing(18)

        self.winner_combo.currentIndexChanged.connect(self._on_winner_changed)
        self.winner_combo.currentIndexChanged.connect(self._update_validation_state)
        if self.second_combo:
            self.second_combo.currentIndexChanged.connect(self._update_validation_state)

    def _build_player_combo(self, placeholder: str) -> QComboBox:
        combo = QComboBox()
        combo.setObjectName("FormatComboBox")
        combo.setMinimumHeight(42)
        combo.setEditable(False)
        combo.setItemDelegate(ComboBoxItemDelegate())
        combo.addItem(placeholder, None)
        for player in self.table.players:
            combo.addItem(player.name, player)
        combo.view().setRowHidden(0, True)
        return combo

    # ======================================================
    # Validation
    # ======================================================
    def _update_validation_state(self):
        if self._is_1v1:
            g1 = self._spin_p1.value()
            g2 = self._spin_p2.value()
            self.confirm_btn.setEnabled((g1, g2) in _VALID_SCORES)
        else:
            winner_ok = self.winner_combo is not None and self.winner_combo.currentIndex() > 0
            if self.second_combo:
                self.confirm_btn.setEnabled(winner_ok and self.second_combo.currentIndex() > 0)
            else:
                self.confirm_btn.setEnabled(winner_ok)

    def _on_winner_changed(self):
        if not self.second_combo:
            return
        winner: Player | None = self.winner_combo.currentData()
        self.second_combo.blockSignals(True)
        self.second_combo.clear()
        self.second_combo.addItem("🥈 Sélectionner le second", None)
        for player in self.table.players:
            if not winner or player.id != winner.id:
                self.second_combo.addItem(player.name, player)
        self.second_combo.view().setRowHidden(0, True)
        self.second_combo.setCurrentIndex(0)
        self.second_combo.blockSignals(False)

    # ======================================================
    # Résultats exposés
    # ======================================================
    def results(self) -> dict[int, int]:
        """player_id -> position (1=vainqueur, 2=défaite/nul, 3=autre)"""
        if self._is_1v1:
            return self._results_bo3()
        return self._results_commander()

    def game_scores(self) -> dict[int, int]:
        """player_id -> games gagnées (BO3). Vide pour Commander."""
        if not self._is_1v1:
            return {}
        p1, p2 = self.table.players
        return {p1.id: self._spin_p1.value(), p2.id: self._spin_p2.value()}

    def _results_bo3(self) -> dict[int, int]:
        p1, p2 = self.table.players
        g1 = self._spin_p1.value()
        g2 = self._spin_p2.value()
        if g1 > g2:
            return {p1.id: 1, p2.id: 2}
        elif g2 > g1:
            return {p2.id: 1, p1.id: 2}
        else:
            # Nul : même position pour déclencher le draw dans standings
            return {p1.id: 2, p2.id: 2}

    def _results_commander(self) -> dict[int, int]:
        results: dict[int, int] = {}
        winner: Player | None = self.winner_combo.currentData() if self.winner_combo else None
        second: Player | None = self.second_combo.currentData() if self.second_combo else None
        if winner:
            results[winner.id] = 1
        if second and (not winner or second.id != winner.id):
            results[second.id] = 2
        for player in self.table.players:
            if player.id not in results:
                results[player.id] = 3
        return results


class ComboBoxItemDelegate(QStyledItemDelegate):
    def sizeHint(self, option, index):
        size = super().sizeHint(option, index)
        size.setHeight(42)
        return size
