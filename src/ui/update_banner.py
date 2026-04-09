"""Bandeau de mise à jour affiché dans la sidebar quand une MAJ est disponible."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QProgressBar, QFrame,
)
from PySide6.QtCore import Qt, Signal

from updater import Updater


class UpdateBanner(QFrame):
    """
    Affiché dans la sidebar dès qu'une nouvelle version est détectée.

    États :
      1. Notification  → bouton "Mettre à jour"
      2. Téléchargement → barre de progression
      3. Prêt          → bouton "Redémarrer"
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("UpdateBanner")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._updater: Updater | None = None
        self._build_ui()
        self.hide()

    # ── Construction UI ───────────────────────────────────────────────────

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        self._title = QLabel("🆕 Mise à jour disponible")
        self._title.setObjectName("UpdateBannerTitle")
        self._title.setAlignment(Qt.AlignCenter)

        self._version_lbl = QLabel("")
        self._version_lbl.setObjectName("UpdateBannerVersion")
        self._version_lbl.setAlignment(Qt.AlignCenter)

        self._progress = QProgressBar()
        self._progress.setObjectName("UpdateProgressBar")
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(6)
        self._progress.hide()

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("UpdateBannerStatus")
        self._status_lbl.setAlignment(Qt.AlignCenter)
        self._status_lbl.hide()

        self._btn = QPushButton("⬇  Mettre à jour")
        self._btn.setObjectName("UpdateButton")
        self._btn.setCursor(Qt.PointingHandCursor)
        self._btn.clicked.connect(self._on_click)

        layout.addWidget(self._title)
        layout.addWidget(self._version_lbl)
        layout.addWidget(self._progress)
        layout.addWidget(self._status_lbl)
        layout.addWidget(self._btn)

    # ── API publique ──────────────────────────────────────────────────────

    def notify(self, new_version: str, download_url: str):
        """Affiche le bandeau avec la version disponible."""
        self._download_url = download_url
        self._version_lbl.setText(f"v{new_version}")
        self._btn.setText("⬇  Mettre à jour")
        self._btn.setEnabled(True)
        self._progress.hide()
        self._status_lbl.hide()
        self.show()

    # ── Slots internes ────────────────────────────────────────────────────

    def _on_click(self):
        if self._updater and self._updater.isRunning():
            return

        btn_text = self._btn.text()
        if "Redémarrer" in btn_text:
            self._updater.apply()
            return

        # Démarrer le téléchargement
        self._btn.setEnabled(False)
        self._btn.setText("Téléchargement…")
        self._progress.setValue(0)
        self._progress.setMaximum(100)
        self._progress.show()
        self._status_lbl.show()
        self._status_lbl.setText("Connexion…")

        self._updater = Updater(self._download_url, self)
        self._updater.progress.connect(self._on_progress)
        self._updater.finished.connect(self._on_finished)
        self._updater.error.connect(self._on_error)
        self._updater.start()

    def _on_progress(self, received: int, total: int):
        if total > 0:
            self._progress.setValue(int(received / total * 100))
            mb_recv  = received / 1_048_576
            mb_total = total    / 1_048_576
            self._status_lbl.setText(f"{mb_recv:.1f} / {mb_total:.1f} Mo")

    def _on_finished(self):
        self._progress.setValue(100)
        self._status_lbl.setText("Téléchargement terminé !")
        self._btn.setText("🔄 Redémarrer")
        self._btn.setEnabled(True)

    def _on_error(self, msg: str):
        self._status_lbl.setText(f"Erreur : {msg}")
        self._btn.setText("⬇  Réessayer")
        self._btn.setEnabled(True)
        self._progress.hide()
