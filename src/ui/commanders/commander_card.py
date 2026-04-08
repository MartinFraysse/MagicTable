from PySide6.QtCore import Qt, Signal, QPoint, QRectF
from PySide6.QtGui import (
    QPainter, QColor, QBrush, QPen, QFont,
    QLinearGradient, QPixmap, QPainterPath,
)
from PySide6.QtWidgets import QFrame

from core.commander import Commander, MTG_COLORS, COLOR_HEX, COLOR_SYMBOLS
from storage.base import DATA_DIR

CARD_W = 160
CARD_H = 210
RADIUS = 12.0


class CommanderCard(QFrame):
    clicked = Signal(int)
    double_clicked = Signal(int)
    context_menu_requested = Signal(int, QPoint)

    def __init__(self, commander: Commander, selected: bool = False, parent=None):
        super().__init__(parent)
        self._commander = commander
        self._selected = selected
        self._hovered = False
        self._pixmap: QPixmap | None = None

        self.setFixedSize(CARD_W, CARD_H)
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
        self._load_pixmap()

    @property
    def commander_id(self) -> int:
        return self._commander.id

    def update_commander(self, commander: Commander):
        self._commander = commander
        self._load_pixmap()
        self.update()

    def set_selected(self, selected: bool):
        if self._selected != selected:
            self._selected = selected
            self.update()

    def _load_pixmap(self):
        self._pixmap = None
        if self._commander.image_path:
            path = DATA_DIR / self._commander.image_path
            if path.exists():
                px = QPixmap(str(path))
                if not px.isNull():
                    self._pixmap = px

    # ------------------------------------------------------------------
    # Paint
    # ------------------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        rect = QRectF(self.rect())

        clip = QPainterPath()
        clip.addRoundedRect(rect, RADIUS, RADIUS)
        painter.setClipPath(clip)

        self._paint_gradient(painter, rect)
        if self._pixmap:
            self._paint_image(painter, rect)
        self._paint_bottom_overlay(painter, rect)
        self._paint_name(painter, rect)
        self._paint_circles(painter, rect)

        painter.setClipping(False)
        if self._selected:
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor("#3ad68a"), 2.5))
            painter.drawRoundedRect(rect.adjusted(1.25, 1.25, -1.25, -1.25), RADIUS, RADIUS)
        elif self._hovered:
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor(255, 255, 255, 60), 1.5))
            painter.drawRoundedRect(rect.adjusted(0.75, 0.75, -0.75, -0.75), RADIUS, RADIUS)

    def _paint_gradient(self, painter: QPainter, rect: QRectF):
        colors = [c for c in MTG_COLORS if c in self._commander.colors]
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())

        if not colors:
            grad.setColorAt(0, QColor("#3a3a3a"))
            grad.setColorAt(1, QColor("#181818"))
        elif len(colors) == 1:
            base = QColor(COLOR_HEX[colors[0]])
            grad.setColorAt(0, base.lighter(130))
            grad.setColorAt(1, base.darker(180))
        else:
            step = 1.0 / (len(colors) - 1)
            for i, code in enumerate(colors):
                grad.setColorAt(i * step, QColor(COLOR_HEX[code]))

        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.NoPen)
        painter.drawRect(rect)

    def _paint_image(self, painter: QPainter, rect: QRectF):
        scaled = self._pixmap.scaled(
            int(rect.width()), int(rect.height()),
            Qt.KeepAspectRatioByExpanding,
            Qt.SmoothTransformation,
        )
        sx = (scaled.width() - int(rect.width())) // 2
        sy = (scaled.height() - int(rect.height())) // 2
        painter.setOpacity(0.50)
        painter.drawPixmap(
            int(rect.x()), int(rect.y()),
            scaled, sx, sy, int(rect.width()), int(rect.height()),
        )
        painter.setOpacity(1.0)

    def _paint_bottom_overlay(self, painter: QPainter, rect: QRectF):
        overlay_y = rect.height() * 0.42
        grad = QLinearGradient(0, overlay_y, 0, rect.height())
        grad.setColorAt(0, QColor(0, 0, 0, 0))
        grad.setColorAt(1, QColor(0, 0, 0, 215))
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.NoPen)
        painter.drawRect(rect)

    def _paint_name(self, painter: QPainter, rect: QRectF):
        name_rect = QRectF(rect.x() + 8, rect.height() - 68, rect.width() - 16, 36)
        font = QFont()
        font.setPixelSize(12)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(name_rect, Qt.AlignBottom | Qt.AlignHCenter | Qt.TextWordWrap, self._commander.name)

    def _paint_circles(self, painter: QPainter, rect: QRectF):
        colors = [c for c in MTG_COLORS if c in self._commander.colors]

        if not colors:
            font = QFont()
            font.setPixelSize(10)
            painter.setFont(font)
            painter.setPen(QColor("#aaaaaa"))
            painter.drawText(
                QRectF(rect.x(), rect.height() - 26, rect.width(), 20),
                Qt.AlignCenter, "Incolore",
            )
            return

        d = 20.0
        sp = 5.0
        n = len(colors)
        total_w = n * d + (n - 1) * sp
        x = rect.x() + (rect.width() - total_w) / 2
        cy = rect.height() - 14.0
        r = d / 2.0

        font = QFont()
        font.setPixelSize(11)
        painter.setFont(font)

        for code in colors:
            circle = QRectF(x, cy - r, d, d)

            # Fond coloré
            painter.setBrush(QBrush(QColor(COLOR_HEX[code])))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(circle)

            # Overlay sombre pour contraster le symbole (sauf blanc)
            if code != "W":
                painter.setBrush(QBrush(QColor(0, 0, 0, 100)))
                painter.drawEllipse(circle)

            # Anneau intérieur (doré pour W, blanc pour les autres)
            painter.setBrush(Qt.NoBrush)
            ring = QColor("#b8960a") if code == "W" else QColor(255, 255, 255, 210)
            painter.setPen(QPen(ring, 1.5))
            painter.drawEllipse(circle.adjusted(1.0, 1.0, -1.0, -1.0))

            # Symbole
            painter.setPen(QColor("#2a1500") if code == "W" else QColor("#ffffff"))
            painter.drawText(circle, Qt.AlignCenter, COLOR_SYMBOLS[code])
            x += d + sp

    # ------------------------------------------------------------------
    # Mouse events
    # ------------------------------------------------------------------

    def enterEvent(self, event):
        self._hovered = True
        self.update()

    def leaveEvent(self, event):
        self._hovered = False
        self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._commander.id)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.double_clicked.emit(self._commander.id)

    def contextMenuEvent(self, event):
        self.context_menu_requested.emit(self._commander.id, event.globalPos())
