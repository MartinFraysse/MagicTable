from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QPushButton, QSizePolicy, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QTimer, QRect
from PySide6.QtGui import QFont, QPainter, QPixmap, QLinearGradient, QBrush, QColor

from core.commander import Commander
from core.round import Round
from storage.base import DATA_DIR
from storage.commanders import CommanderStorage


def _load_commanders_map() -> dict[str, str]:
    """Retourne {nom_commandant: image_path}."""
    raw = CommanderStorage.load()
    return {
        c.name: c.image_path
        for c in (Commander.from_dict(d) for d in raw)
        if c.image_path
    }


_ROW_BG = QColor(0x16, 0x16, 0x16)


class _PairingRow(QFrame):
    """Ligne de pairing avec images des commandants en fond."""

    def __init__(self, img_paths: list[str | None], parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._pixmaps: list[QPixmap | None] = []
        for path in img_paths:
            if path:
                px = QPixmap(str(DATA_DIR / path))
                self._pixmaps.append(px if not px.isNull() else None)
            else:
                self._pixmaps.append(None)

    def paintEvent(self, event):
        # 1. Fond QSS en premier
        super().paintEvent(event)

        visible = [px for px in self._pixmaps if px is not None]
        if not visible:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        rect = self.rect()
        n = len(self._pixmaps)
        slot_w = rect.width() // n

        for i, px in enumerate(self._pixmaps):
            if px is None:
                continue

            slot = QRect(i * slot_w, 0, slot_w if i < n - 1 else rect.width() - i * slot_w, rect.height())

            # Image plein-cadre sur le slot
            scaled = px.scaled(slot.width(), slot.height(),
                               Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            src_x = max(0, (scaled.width() - slot.width()) // 2)
            src_y = max(0, (scaled.height() - slot.height()) // 5)
            src_rect = QRect(src_x, src_y, slot.width(), slot.height())

            painter.save()
            painter.setOpacity(0.65)
            painter.drawPixmap(slot, scaled, src_rect)
            painter.setOpacity(1.0)
            painter.restore()

            # Gradient : fondu sur le bord intérieur (vers le centre)
            grad = QLinearGradient(slot.left(), 0, slot.right(), 0)
            if i == 0:
                # Image gauche : visible à gauche, fondu vers la droite
                grad.setColorAt(0.00, QColor(_ROW_BG.red(), _ROW_BG.green(), _ROW_BG.blue(), 0))
                grad.setColorAt(0.55, QColor(_ROW_BG.red(), _ROW_BG.green(), _ROW_BG.blue(), 80))
                grad.setColorAt(0.75, QColor(_ROW_BG.red(), _ROW_BG.green(), _ROW_BG.blue(), 200))
                grad.setColorAt(1.00, QColor(_ROW_BG.red(), _ROW_BG.green(), _ROW_BG.blue(), 255))
            elif i == n - 1:
                # Image droite : fondu depuis la gauche, visible à droite
                grad.setColorAt(0.00, QColor(_ROW_BG.red(), _ROW_BG.green(), _ROW_BG.blue(), 255))
                grad.setColorAt(0.25, QColor(_ROW_BG.red(), _ROW_BG.green(), _ROW_BG.blue(), 200))
                grad.setColorAt(0.45, QColor(_ROW_BG.red(), _ROW_BG.green(), _ROW_BG.blue(), 80))
                grad.setColorAt(1.00, QColor(_ROW_BG.red(), _ROW_BG.green(), _ROW_BG.blue(), 0))
            else:
                # Image centrale (multiplayer) : fondu des deux côtés
                grad.setColorAt(0.00, QColor(_ROW_BG.red(), _ROW_BG.green(), _ROW_BG.blue(), 255))
                grad.setColorAt(0.20, QColor(_ROW_BG.red(), _ROW_BG.green(), _ROW_BG.blue(), 80))
                grad.setColorAt(0.50, QColor(_ROW_BG.red(), _ROW_BG.green(), _ROW_BG.blue(), 0))
                grad.setColorAt(0.80, QColor(_ROW_BG.red(), _ROW_BG.green(), _ROW_BG.blue(), 80))
                grad.setColorAt(1.00, QColor(_ROW_BG.red(), _ROW_BG.green(), _ROW_BG.blue(), 255))

            painter.fillRect(slot, QBrush(grad))

        painter.end()


class PairingsWindow(QWidget):
    """Fenêtre de projection des pairings avec timer."""

    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Pairings - Projection")
        self.setMinimumSize(1000, 700)
        self.setAttribute(Qt.WA_DeleteOnClose, False)

        self._round: Round | None = None
        self._remaining_seconds = 0
        self._is_fullscreen = False

        # Timer interne pour l'affichage
        self._display_timer = QTimer(self)
        self._display_timer.timeout.connect(self._update_timer_display)
        self._display_timer.start(1000)

        self._setup_ui()
        self._apply_styles()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(0)
        root.setContentsMargins(0, 0, 0, 0)

        # === Header bar ===
        header = QFrame()
        header.setObjectName("HeaderBar")
        header.setFixedHeight(100)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(40, 0, 40, 0)

        # Titre du round (gauche)
        self.round_title = QLabel("Round 1")
        self.round_title.setObjectName("RoundTitle")
        title_font = QFont()
        title_font.setPointSize(32)
        title_font.setBold(True)
        self.round_title.setFont(title_font)

        # Timer (centre)
        self.timer_label = QLabel("50:00")
        self.timer_label.setObjectName("TimerLabel")
        self.timer_label.setAlignment(Qt.AlignCenter)
        timer_font = QFont()
        timer_font.setPointSize(52)
        timer_font.setBold(True)
        self.timer_label.setFont(timer_font)

        # Bouton plein écran (droite)
        self.fullscreen_btn = QPushButton("⛶")
        self.fullscreen_btn.setObjectName("FullscreenBtn")
        self.fullscreen_btn.setFixedSize(60, 60)
        self.fullscreen_btn.setToolTip("Plein écran (F11)")
        self.fullscreen_btn.clicked.connect(self._toggle_fullscreen)

        header_layout.addWidget(self.round_title)
        header_layout.addStretch()
        header_layout.addWidget(self.timer_label)
        header_layout.addStretch()
        header_layout.addWidget(self.fullscreen_btn)

        root.addWidget(header)

        # === Liste des pairings ===
        scroll = QScrollArea()
        scroll.setObjectName("PairingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        self.pairings_container = QWidget()
        self.pairings_container.setObjectName("PairingsContainer")
        self.pairings_layout = QVBoxLayout(self.pairings_container)
        self.pairings_layout.setSpacing(4)
        self.pairings_layout.setContentsMargins(40, 30, 40, 30)

        scroll.setWidget(self.pairings_container)
        root.addWidget(scroll, 1)

    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #0a0a0a;
                color: #ffffff;
            }

            #HeaderBar {
                background-color: #111111;
                border-bottom: 3px solid #22c55e;
            }

            #RoundTitle {
                color: #888888;
            }

            #TimerLabel {
                color: #22c55e;
            }

            #FullscreenBtn {
                background-color: #1a1a1a;
                border: 2px solid #333333;
                border-radius: 12px;
                color: #888888;
                font-size: 28px;
            }

            #FullscreenBtn:hover {
                background-color: #222222;
                border-color: #22c55e;
                color: #22c55e;
            }

            #PairingsScroll {
                background: transparent;
            }

            #PairingsContainer {
                background: transparent;
            }

            #TableRow {
                background-color: #161616;
                border: 1px solid #2a2a2a;
                border-left: 4px solid #22c55e;
                border-radius: 8px;
            }

            #TableRow[status="finished"] {
                background-color: #1a1a1a;
                border-left: 4px solid #666666;
                opacity: 0.7;
            }

            #TableRow[status="bye"] {
                background-color: #1a1a1a;
                border-left: 4px solid #eab308;
            }

            QLabel {
                background: transparent;
            }

            #TableNumber {
                color: #22c55e;
                font-size: 22px;
                font-weight: bold;
                min-width: 120px;
                background: transparent;
            }

            #PlayerName {
                color: #ffffff;
                font-size: 26px;
                font-weight: 500;
                padding: 8px 20px;
                background: transparent;
            }

            #VsSeparator {
                color: #555555;
                font-size: 20px;
                padding: 0 10px;
                background: transparent;
            }

            #StatusBadge {
                color: #22c55e;
                font-size: 18px;
                padding: 6px 16px;
                background-color: #1a2e1a;
                border-radius: 8px;
            }

            #ByeBadge {
                color: #eab308;
                font-size: 18px;
                padding: 6px 16px;
                background-color: #2a2510;
                border-radius: 8px;
            }

            QScrollBar:vertical {
                background: #111111;
                width: 10px;
                border-radius: 5px;
            }

            QScrollBar::handle:vertical {
                background: #333333;
                border-radius: 5px;
                min-height: 40px;
            }

            QScrollBar::handle:vertical:hover {
                background: #22c55e;
            }

            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0;
            }
        """)

    def set_round(self, round_: Round):
        """Met à jour l'affichage avec le round donné."""
        self._round = round_

        if not round_:
            self.round_title.setText("Aucun round")
            self._clear_pairings()
            return

        self.round_title.setText(f"Round {round_.number}")
        self._populate_pairings()

    def set_remaining_seconds(self, seconds: int):
        """Met à jour le temps restant."""
        self._remaining_seconds = seconds
        self._update_timer_display()

    def _update_timer_display(self):
        """Met à jour l'affichage du timer."""
        minutes = self._remaining_seconds // 60
        seconds = self._remaining_seconds % 60

        self.timer_label.setText(f"{minutes:02d}:{seconds:02d}")

        # Changer la couleur selon le temps restant
        if self._remaining_seconds <= 300:
            self.timer_label.setStyleSheet("color: #ef4444; font-size: 52px; font-weight: bold;")
        elif self._remaining_seconds <= 600:
            self.timer_label.setStyleSheet("color: #fbbf24; font-size: 52px; font-weight: bold;")
        else:
            self.timer_label.setStyleSheet("color: #4ade80; font-size: 52px; font-weight: bold;")

    def _clear_pairings(self):
        """Vide la liste des pairings."""
        while self.pairings_layout.count():
            item = self.pairings_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def _populate_pairings(self):
        """Remplit la liste avec les pairings du round."""
        self._clear_pairings()

        if not self._round or not self._round.tables:
            return

        commanders_map = _load_commanders_map()
        for table in self._round.tables:
            row = self._create_table_row(table, commanders_map)
            self.pairings_layout.addWidget(row)

        # Spacer en bas
        self.pairings_layout.addStretch()

    def _create_table_row(self, table, commanders_map: dict | None = None) -> QFrame:
        """Crée une ligne pour une table."""
        img_paths = []
        if commanders_map:
            for player in table.players:
                img_paths.append(commanders_map.get(player.commander, None) if player.commander else None)
        row = _PairingRow(img_paths)
        row.setObjectName("TableRow")
        row.setMinimumHeight(70)
        row.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QHBoxLayout(row)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(0)

        # Numéro de table
        table_num = QLabel(f"Table {table.number}")
        table_num.setObjectName("TableNumber")
        layout.addWidget(table_num)

        # Séparateur
        layout.addSpacing(30)

        # Cas BYE
        if len(table.players) == 1:
            player = table.players[0]

            player_label = QLabel(player.name)
            player_label.setObjectName("PlayerName")
            layout.addWidget(player_label)

            layout.addStretch()

            bye_badge = QLabel("🎫 BYE")
            bye_badge.setObjectName("ByeBadge")
            layout.addWidget(bye_badge)

            row.setProperty("status", "bye")
            row.style().unpolish(row)
            row.style().polish(row)
            return row

        # Joueurs
        players = table.players

        if len(players) == 2:
            # Format 1v1
            p1 = QLabel(players[0].name)
            p1.setObjectName("PlayerName")
            layout.addWidget(p1)

            vs = QLabel("⚔")
            vs.setObjectName("VsSeparator")
            layout.addWidget(vs)

            p2 = QLabel(players[1].name)
            p2.setObjectName("PlayerName")
            layout.addWidget(p2)
        else:
            # Format multiplayer (3-4 joueurs)
            for i, player in enumerate(players):
                if i > 0:
                    sep = QLabel("•")
                    sep.setObjectName("VsSeparator")
                    layout.addWidget(sep)

                p_label = QLabel(player.name)
                p_label.setObjectName("PlayerName")
                layout.addWidget(p_label)

        layout.addStretch()

        # Status si terminé
        if table.finished:
            winner = None
            for player in table.players:
                if table.results.get(player.id) == 1:
                    winner = player
                    break

            if winner:
                status = QLabel(f"🏆 {winner.name}")
            else:
                status = QLabel("✔ Terminée")
            status.setObjectName("StatusBadge")
            layout.addWidget(status)

            row.setProperty("status", "finished")
            row.style().unpolish(row)
            row.style().polish(row)

        return row

    def _toggle_fullscreen(self):
        """Bascule entre plein écran et fenêtré."""
        if self._is_fullscreen:
            self.showNormal()
            self.fullscreen_btn.setText("⛶")
            self._is_fullscreen = False
        else:
            self.showFullScreen()
            self.fullscreen_btn.setText("✕")
            self._is_fullscreen = True

    def refresh(self):
        """Rafraîchit l'affichage des pairings."""
        if self._round:
            self._populate_pairings()

    def keyPressEvent(self, event):
        """Gère les raccourcis clavier."""
        if event.key() == Qt.Key_Escape:
            if self._is_fullscreen:
                self._toggle_fullscreen()
            else:
                self.close()
        elif event.key() == Qt.Key_F11 or event.key() == Qt.Key_F:
            self._toggle_fullscreen()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event):
        """Émet le signal closed quand la fenêtre se ferme."""
        self.closed.emit()
        super().closeEvent(event)
