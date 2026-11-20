"""Delegate de la liste des joueurs inscrits (zone de lancement)."""

from PySide6.QtCore import Qt, QRect, QSize, QModelIndex
from PySide6.QtGui import QPainter, QBrush, QColor, QPixmap, QLinearGradient
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QStyle

from storage.base import DATA_DIR


_LIST_BG = QColor(0x0f, 0x24, 0x1d)  # fond LaunchPlayersList


class PlayerListDelegate(QStyledItemDelegate):
    """Delegate pour dessiner un fond arrondi sur les items de la liste."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hover_color = QColor(63, 210, 125, 50)
        self._selected_color = QColor(63, 210, 125, 90)
        self._pixmap_cache: dict[str, QPixmap | None] = {}

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        rect = option.rect

        # === Image commandant en fond plein-cadre ===
        image_path = index.data(Qt.UserRole + 2)
        if image_path:
            full_path = str(DATA_DIR / image_path)
            if full_path not in self._pixmap_cache:
                px = QPixmap(full_path)
                self._pixmap_cache[full_path] = px if not px.isNull() else None
            px = self._pixmap_cache.get(full_path)
            if px:
                # 1. Fond de base
                painter.fillRect(rect, _LIST_BG)

                # 2. Image sur la moitié droite uniquement
                half_x = rect.left() + rect.width() // 2
                img_rect = QRect(half_x, rect.top(), rect.width() - rect.width() // 2, rect.height())

                scaled = px.scaled(
                    img_rect.width(), img_rect.height(),
                    Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
                )
                src_x = max(0, (scaled.width() - img_rect.width()) // 2)
                src_y = max(0, (scaled.height() - img_rect.height()) // 5)
                src_rect = QRect(src_x, src_y, img_rect.width(), img_rect.height())

                painter.save()
                painter.setOpacity(0.60)
                painter.drawPixmap(img_rect, scaled, src_rect)
                painter.setOpacity(1.0)
                painter.restore()

                # 3. Gradient : opaque à gauche, fondu progressif, image nette à droite
                fade_start = half_x - rect.width() // 10
                grad = QLinearGradient(fade_start, 0, rect.right(), 0)
                grad.setColorAt(0.00, QColor(0x0f, 0x24, 0x1d, 255))
                grad.setColorAt(0.45, QColor(0x0f, 0x24, 0x1d, 230))
                grad.setColorAt(0.68, QColor(0x0f, 0x24, 0x1d, 120))
                grad.setColorAt(0.85, QColor(0x0f, 0x24, 0x1d, 30))
                grad.setColorAt(1.00, QColor(0x0f, 0x24, 0x1d, 0))
                painter.fillRect(QRect(fade_start, rect.top(), rect.right() - fade_start, rect.height()), QBrush(grad))

        # === Fond hover/sélection arrondi (par-dessus l'image) ===
        is_selected = bool(option.state & QStyle.State_Selected)
        is_hovered = bool(option.state & QStyle.State_MouseOver)

        if is_selected or is_hovered:
            painter.save()
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.NoPen)

            item_rect = QRect(
                rect.left() + 4,
                rect.top() + 2,
                rect.width() - 8,
                rect.height() - 4
            )

            if is_selected:
                painter.setBrush(QBrush(self._selected_color))
            else:
                painter.setBrush(QBrush(self._hover_color))

            painter.drawRoundedRect(item_rect, 6, 6)
            painter.restore()

        # Dessiner le contenu normal (texte)
        super().paint(painter, option, index)

    def sizeHint(self, option, index) -> QSize:
        return QSize(0, 50)
