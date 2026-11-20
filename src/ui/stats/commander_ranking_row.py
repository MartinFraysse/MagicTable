"""Ligne de classement de commandant (miniature circulaire + nom + compteur)."""

from PySide6.QtCore import Qt, QRectF, QRect
from PySide6.QtGui import QPainter, QPixmap, QColor, QPainterPath, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QFrame

from storage.base import DATA_DIR


class _CommanderThumb(QFrame):
    """Image circulaire miniature d'un commandant."""

    def __init__(self, img_path: str | None, size: int = 44, parent=None):
        super().__init__(parent)
        self._size = size
        self._pixmap: QPixmap | None = None
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WA_StyledBackground, False)
        if img_path:
            px = QPixmap(str(DATA_DIR / img_path))
            if not px.isNull():
                self._pixmap = px

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        s = self._size
        circle = QRectF(0, 0, s, s)

        clip = QPainterPath()
        clip.addEllipse(circle)
        painter.setClipPath(clip)

        if self._pixmap:
            scaled = self._pixmap.scaled(s, s, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            sx = (scaled.width() - s) // 2
            sy = max(0, (scaled.height() - s) // 5)
            painter.drawPixmap(QRect(0, 0, s, s), scaled, QRect(sx, sy, s, s))
        else:
            painter.fillRect(QRect(0, 0, s, s), QColor("#1a3d2e"))

        painter.setClipping(False)
        painter.setPen(QPen(QColor("#2f6f55"), 1.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(circle.adjusted(0.75, 0.75, -0.75, -0.75))
        painter.end()


class CommanderRankingRow(QFrame):
    """Ligne de classement : rang + image circulaire + nom + compteur."""

    _RANK_COLOR = {1: "#FFD700", 2: "#B0B8C1", 3: "#CD7F32"}

    def __init__(self, rank: int, name: str, count: int, suffix: str,
                 img_path: str | None, parent=None):
        super().__init__(parent)
        self.setObjectName("RankingRow")
        self.setFixedHeight(58)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 4, 14, 4)
        lay.setSpacing(10)

        # Numéro de rang (coloré pour le top 3)
        rk_lbl = QLabel(f"#{rank}")
        color = self._RANK_COLOR.get(rank, "")
        if color:
            rk_lbl.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 14px;")
        else:
            rk_lbl.setObjectName("RankingNumber")
        rk_lbl.setFixedWidth(34)
        rk_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(rk_lbl)

        # Image circulaire
        lay.addWidget(_CommanderThumb(img_path, size=46))

        # Nom
        name_lbl = QLabel(name)
        name_lbl.setObjectName("StatsLabel")
        lay.addWidget(name_lbl, 1)

        # Compteur (en gras)
        val_lbl = QLabel(f"<b>{count}</b> {suffix}")
        val_lbl.setObjectName("StatsValue")
        val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay.addWidget(val_lbl)
