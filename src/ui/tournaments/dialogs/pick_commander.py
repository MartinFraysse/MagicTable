"""Dialog de choix du commandant d’un joueur."""

from PySide6.QtCore import Qt, QRect, QRectF, QSize, QModelIndex
from PySide6.QtGui import QPainter, QBrush, QColor, QPen, QFont
from PySide6.QtWidgets import (
    QDialog, QListWidgetItem, QLineEdit, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QStyledItemDelegate, QStyleOptionViewItem, QStyle
)

from core.commander import Commander, MTG_COLORS, COLOR_HEX, COLOR_SYMBOLS
from storage.commanders import CommanderStorage
from ui.commanders.dialogs.create_commander import CreateCommanderDialog


class CommanderPickDelegate(QStyledItemDelegate):
    _D = 26
    _SP = 5

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        is_selected = bool(option.state & QStyle.State_Selected)
        is_hovered = bool(option.state & QStyle.State_MouseOver)

        if is_selected or is_hovered:
            painter.save()
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.NoPen)
            r = QRect(option.rect.left() + 4, option.rect.top() + 2,
                      option.rect.width() - 8, option.rect.height() - 4)
            painter.setBrush(QBrush(QColor(63, 210, 125, 77 if is_selected else 38)))
            painter.drawRoundedRect(r, 6, 6)
            painter.restore()

        colors = index.data(Qt.UserRole + 1) or []
        n = len(colors)
        circles_w = n * (self._D + self._SP) - self._SP + 16 if n else 0

        name_rect = QRect(option.rect.left() + 12, option.rect.top(),
                          option.rect.width() - circles_w - 16, option.rect.height())

        painter.save()
        font = QFont()
        font.setPixelSize(13)
        painter.setFont(font)
        painter.setPen(QColor("#eafff6"))
        painter.drawText(name_rect, Qt.AlignVCenter | Qt.AlignLeft,
                         index.data(Qt.DisplayRole))

        if colors:
            painter.setRenderHint(QPainter.Antialiasing)
            r2 = self._D / 2
            x = float(option.rect.right() - circles_w + 8)
            cy = float(option.rect.center().y())
            font2 = QFont()
            font2.setPixelSize(14)
            painter.setFont(font2)
            for code in colors:
                circle = QRectF(x, cy - r2, self._D, self._D)

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
                x += self._D + self._SP

        painter.restore()

    def sizeHint(self, option, index) -> QSize:
        return QSize(0, 46)


class PickCommanderDialog(QDialog):
    """Dialog pour choisir un commandant depuis la liste créée."""

    def __init__(self, parent, current_commander: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Choisir un commandant")
        self.setModal(True)
        self.setObjectName("BrowsePlayersDialog")
        self.setFixedSize(500, 500)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._selected_name: str = ""
        self._filter_duel: bool = False

        raw = CommanderStorage.load()
        self._commanders: list[Commander] = sorted(
            [Commander.from_dict(d) for d in raw],
            key=lambda c: c.name.lower(),
        )

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 14)

        title = QLabel("🛡️ Choisir un commandant")
        title.setObjectName("LaunchSectionTitle")
        layout.addWidget(title)

        search_row = QHBoxLayout()
        search_row.setSpacing(8)

        self.filter_input = QLineEdit()
        self.filter_input.setObjectName("LaunchPlayerInput")
        self.filter_input.setPlaceholderText("Rechercher…")
        self.filter_input.textChanged.connect(self._refresh_list)
        search_row.addWidget(self.filter_input, 1)

        self._duel_btn = QPushButton("⚔️ Duel")
        self._duel_btn.setObjectName("FilterToggleButton")
        self._duel_btn.setCheckable(True)
        self._duel_btn.setFixedHeight(30)
        self._duel_btn.setCursor(Qt.PointingHandCursor)
        self._duel_btn.toggled.connect(self._on_duel_toggled)
        search_row.addWidget(self._duel_btn)

        layout.addLayout(search_row)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("LaunchPlayersList")
        self.list_widget.setSpacing(2)
        self.list_widget.setMouseTracking(True)
        self.list_widget.viewport().setMouseTracking(True)
        self.list_widget.setItemDelegate(CommanderPickDelegate(self.list_widget))
        self.list_widget.itemClicked.connect(self._on_click)
        self.list_widget.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self.list_widget, 1)

        hint = QLabel("Double-clic ou ✓ Choisir pour confirmer")
        hint.setObjectName("BracketRoundSubtitle")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        clear_btn = QPushButton("✕ Retirer")
        clear_btn.setObjectName("BracketCancelButton")
        clear_btn.setFixedHeight(32)
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self._clear_and_accept)

        new_btn = QPushButton("➕ Nouveau")
        new_btn.setObjectName("LaunchPrimaryButton")
        new_btn.setFixedHeight(32)
        new_btn.setCursor(Qt.PointingHandCursor)
        new_btn.clicked.connect(self._create_commander)

        cancel_btn = QPushButton("Annuler")
        cancel_btn.setObjectName("BracketCancelButton")
        cancel_btn.setFixedHeight(32)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.clicked.connect(self.reject)

        self.ok_btn = QPushButton("✓ Choisir")
        self.ok_btn.setObjectName("LaunchPrimaryButton")
        self.ok_btn.setFixedHeight(32)
        self.ok_btn.setEnabled(False)
        self.ok_btn.setCursor(Qt.PointingHandCursor)
        self.ok_btn.clicked.connect(self.accept)

        btn_row.addWidget(clear_btn)
        btn_row.addWidget(new_btn)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self.ok_btn)
        layout.addLayout(btn_row)

        self._refresh_list()

        if current_commander:
            for i in range(self.list_widget.count()):
                item = self.list_widget.item(i)
                if item and item.text() == current_commander:
                    self.list_widget.setCurrentItem(item)
                    self._selected_name = current_commander
                    self.ok_btn.setEnabled(True)
                    break

    def _on_duel_toggled(self, checked: bool):
        self._filter_duel = checked
        self._refresh_list()

    def _refresh_list(self):
        f = self.filter_input.text().lower().strip()
        self.list_widget.clear()
        for commander in self._commanders:
            if self._filter_duel and not commander.duel:
                continue
            if f and f not in commander.name.lower():
                continue
            item = QListWidgetItem(commander.name)
            item.setData(Qt.UserRole + 1, [c for c in MTG_COLORS if c in commander.colors])
            self.list_widget.addItem(item)

    def _on_click(self, item: QListWidgetItem):
        self._selected_name = item.text()
        self.ok_btn.setEnabled(True)

    def _on_double_click(self, item: QListWidgetItem):
        self._selected_name = item.text()
        self.accept()

    def _create_commander(self):
        existing_names = [c.name for c in self._commanders]
        dialog = CreateCommanderDialog(self, existing_names=existing_names)
        if not dialog.exec():
            return

        data = dialog.get_data()
        raw = CommanderStorage.load()
        commanders = [Commander.from_dict(d) for d in raw]
        next_id = max((c.id for c in commanders), default=0) + 1

        new_commander = Commander(
            id=next_id,
            name=data["name"],
            colors=data["colors"],
            image_path=data.get("image_path"),
            duel=data.get("duel", False),
        )
        commanders.append(new_commander)
        CommanderStorage.save([c.to_dict() for c in commanders])

        self._commanders = sorted(commanders, key=lambda c: c.name.lower())
        self.filter_input.clear()
        self._refresh_list()

        self._selected_name = new_commander.name
        self.ok_btn.setEnabled(True)
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item and item.text() == new_commander.name:
                self.list_widget.setCurrentItem(item)
                self.list_widget.scrollToItem(item)
                break

    def _clear_and_accept(self):
        self._selected_name = ""
        self.accept()

    def get_commander_name(self) -> str:
        return self._selected_name
