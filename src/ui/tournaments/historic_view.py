from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QPushButton,
    QFrame,
)


class HistoricView(QWidget):
    """
    Vue d’accès à l’historique des tournois.

    Responsabilité :
    - Fournir un point d’entrée vers l’historique
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("HistoricView")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._build_ui()


    # =========================
    # UI
    # =========================
    def _build_ui(self):
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        container = QFrame()
        container.setObjectName("HistoricContainerInner")
        container.setAttribute(Qt.WA_StyledBackground, True)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(12, 8, 12, 8)

        layout.addStretch()

        history_btn = QPushButton("📜 Historique des tournois")
        history_btn.setObjectName("HistoricPrimaryButton")
        history_btn.setCursor(Qt.PointingHandCursor)

        layout.addWidget(history_btn)

        root_layout.addWidget(container, 1)