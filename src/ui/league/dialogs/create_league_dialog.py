"""Dialog de création / édition d'une ligue."""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QComboBox, QSpinBox, QLabel,
    QPushButton, QFrame, QDialogButtonBox,
)
from PySide6.QtCore import Qt

from core.league import League, DEFAULT_SCORING, DEFAULT_PARTICIPATION_PTS, next_free_league_id

FORMATS = [
    "👑 Commander",
    "⚔️ Duel Commander",
    "🃏 Draft",
    "🏆 AP",
    "⚡ Pokemon",
    "🔥 Rise",
]

_POSITION_LABELS = ["1er", "2e", "3e", "4e", "5e", "6e", "7e", "8e"]


class CreateLeagueDialog(QDialog):
    """
    Créer une nouvelle ligue ou éditer une ligue existante.

    Paramètres :
      leagues   — liste actuelle (pour générer un nouvel ID)
      league    — ligue existante à éditer (None = création)
    """

    def __init__(self, parent, leagues: list[League], league: League | None = None):
        super().__init__(parent)
        self._leagues = leagues
        self._league = league
        self._editing = league is not None

        self.setWindowTitle("Modifier la ligue" if self._editing else "Nouvelle ligue")
        self.setMinimumWidth(420)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("CreateLeagueDialog")

        self._build_ui()
        if self._editing:
            self._populate(league)

    # ── UI ───────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(16)
        root.setContentsMargins(24, 24, 24, 24)

        # ── Infos de base ────────────────────────────────────────────────────
        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Ex. FNM Commander")
        form.addRow("Nom :", self._name_edit)

        self._season_edit = QLineEdit()
        self._season_edit.setPlaceholderText("Ex. 2026")
        form.addRow("Saison :", self._season_edit)

        self._format_combo = QComboBox()
        for f in FORMATS:
            self._format_combo.addItem(f)
        form.addRow("Format :", self._format_combo)

        root.addLayout(form)

        # ── Barème ───────────────────────────────────────────────────────────
        scoring_label = QLabel("Barème de points")
        scoring_label.setObjectName("SectionLabel")
        root.addWidget(scoring_label)

        scoring_frame = QFrame()
        scoring_frame.setObjectName("LeagueScoringFrame")
        scoring_layout = QVBoxLayout(scoring_frame)
        scoring_layout.setSpacing(6)
        scoring_layout.setContentsMargins(12, 12, 12, 12)

        self._scoring_spins: list[QSpinBox] = []
        for i, label in enumerate(_POSITION_LABELS):
            row = QHBoxLayout()
            lbl = QLabel(f"{label} place :")
            lbl.setObjectName("ScoringPositionLabel")
            lbl.setFixedWidth(90)
            spin = QSpinBox()
            spin.setRange(0, 999)
            spin.setValue(DEFAULT_SCORING.get(i + 1, DEFAULT_PARTICIPATION_PTS))
            spin.setSuffix(" pt(s)")
            spin.setFixedWidth(110)
            row.addWidget(lbl)
            row.addWidget(spin)
            row.addStretch()
            scoring_layout.addLayout(row)
            self._scoring_spins.append(spin)

        # Participation
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setObjectName("ScoringSeparator")
        scoring_layout.addWidget(sep)

        part_row = QHBoxLayout()
        part_lbl = QLabel("Autres places :")
        part_lbl.setFixedWidth(90)
        self._participation_spin = QSpinBox()
        self._participation_spin.setRange(0, 99)
        self._participation_spin.setValue(DEFAULT_PARTICIPATION_PTS)
        self._participation_spin.setSuffix(" pt(s)")
        self._participation_spin.setFixedWidth(110)
        part_row.addWidget(part_lbl)
        part_row.addWidget(self._participation_spin)
        part_row.addStretch()
        scoring_layout.addLayout(part_row)

        root.addWidget(scoring_frame)

        # ── Boutons ──────────────────────────────────────────────────────────
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _populate(self, league: League) -> None:
        self._name_edit.setText(league.name)
        self._season_edit.setText(league.season)
        idx = self._format_combo.findText(league.format)
        if idx >= 0:
            self._format_combo.setCurrentIndex(idx)
        for i, spin in enumerate(self._scoring_spins):
            spin.setValue(league.scoring.get(i + 1, league.participation_pts))
        self._participation_spin.setValue(league.participation_pts)

    # ── Validation ───────────────────────────────────────────────────────────

    def _on_accept(self) -> None:
        if not self._name_edit.text().strip():
            self._name_edit.setFocus()
            return
        self.accept()

    # ── Résultat ─────────────────────────────────────────────────────────────

    def build_league(self) -> League:
        """Retourne la League créée ou mise à jour."""
        scoring = {
            i + 1: spin.value()
            for i, spin in enumerate(self._scoring_spins)
        }
        if self._editing:
            lg = self._league
            lg.name = self._name_edit.text().strip()
            lg.season = self._season_edit.text().strip()
            lg.format = self._format_combo.currentText()
            lg.scoring = scoring
            lg.participation_pts = self._participation_spin.value()
            return lg
        else:
            return League(
                id=next_free_league_id(self._leagues),
                name=self._name_edit.text().strip(),
                format=self._format_combo.currentText(),
                season=self._season_edit.text().strip(),
                scoring=scoring,
                participation_pts=self._participation_spin.value(),
            )
