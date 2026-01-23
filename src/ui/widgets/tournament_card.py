from PySide6.QtCore import Qt, Signal, QMimeData, QPoint
from PySide6.QtGui import QDrag
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QLabel,
    QMenu,
)
import json

from core.tournament import Tournament


class TournamentCard(QFrame):
    """
    Carte représentant un tournoi (UI uniquement).
    """

    # Signaux vers la vue parente
    request_edit = Signal(Tournament)
    request_launch = Signal(Tournament)
    request_delete = Signal(Tournament)
    card_selected = Signal(object)

    def __init__(self, tournament: Tournament, parent=None):
        super().__init__(parent)

        self.tournament = tournament
        self._drag_start_pos: QPoint | None = None

        # État externe (fourni par UpcomingView)
        self.launch_available: bool = True

        self.setObjectName("TournamentCard")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFocusPolicy(Qt.StrongFocus)

        self._build_ui()
        self._refresh()

    # =========================
    # UI
    # =========================
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        # === NOM ===
        self.title_label = QLabel()
        self.title_label.setObjectName("TournamentCardTitle")
        self.title_label.setWordWrap(False)

        # === FORMAT ===
        self.format_label = QLabel()
        self.format_label.setObjectName("TournamentCardFormat")

        # === DATE • JOUEURS ===
        self.meta_label = QLabel()
        self.meta_label.setObjectName("TournamentCardMeta")

        layout.addWidget(self.title_label)
        layout.addWidget(self.format_label)
        layout.addWidget(self.meta_label)

    def _refresh(self):
        """
        Rafraîchit l'affichage depuis l'objet Tournament.
        """
        t = self.tournament

        self.title_label.setText(t.name)
        self.title_label.setToolTip(t.name)
        self.format_label.setText(t.format)
        self.meta_label.setText(
            f"{t.date} • {t.player_count} joueurs"
        )

    # =========================
    # Context menu (clic droit)
    # =========================
    def contextMenuEvent(self, event):
        menu = QMenu(self)

        edit_action = menu.addAction("✏️ Modifier le tournoi")
        menu.addSeparator()

        launch_action = menu.addAction("🚀 Envoyer vers Launch")
        launch_action.setEnabled(self.launch_available)

        menu.addSeparator()
        delete_action = menu.addAction("🗑️ Supprimer le tournoi")

        action = menu.exec(event.globalPos())

        if action == edit_action:
            self.request_edit.emit(self.tournament)
        elif action == launch_action:
            self.request_launch.emit(self.tournament)
        elif action == delete_action:
            self.request_delete.emit(self.tournament)

    # =========================
    # Mouse / Selection / Drag
    # =========================
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Sélection
            self.setFocus()
            self.card_selected.emit(self)

            # Préparer le drag
            self._drag_start_pos = event.pos()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not self._drag_start_pos:
            return

        if not (event.buttons() & Qt.LeftButton):
            return

        distance = (event.pos() - self._drag_start_pos).manhattanLength()
        if distance < 8:
            return

        self._start_drag()

    def _start_drag(self):
        drag = QDrag(self)
        mime = QMimeData()

        payload = json.dumps(self.tournament.to_dict())
        mime.setData(
            "application/x-magictable-tournament",
            payload.encode("utf-8")
        )

        drag.setMimeData(mime)

        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(pixmap.rect().center())

        drag.exec(Qt.MoveAction)
