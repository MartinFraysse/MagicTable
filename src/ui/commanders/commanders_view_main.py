from PySide6.QtCore import Qt, QModelIndex, QRectF
from PySide6.QtGui import QPalette, QColor, QPainter, QBrush, QPen, QFont, QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QMenu,
    QAbstractItemView,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QStyle,
    QLineEdit,
)

from core.commander import Commander, MTG_COLORS, COLOR_SYMBOLS, COLOR_HEX, COLOR_LABELS
from storage.commanders import CommanderStorage
from ui.commanders.dialogs.create_commander import CreateCommanderDialog


class RowBackgroundDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._hover_color = QColor(20, 53, 38)
        self._selected_color = QColor(24, 70, 48)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        table = option.widget
        if table is None:
            super().paint(painter, option, index)
            return

        col = index.column()
        row = index.row()
        col_count = table.columnCount()

        is_selected = table.selectionModel().isRowSelected(row, index.parent())
        cursor_pos = table.viewport().mapFromGlobal(table.cursor().pos())
        hovered_index = table.indexAt(cursor_pos)
        is_hovered = hovered_index.isValid() and hovered_index.row() == row and not is_selected

        if is_selected or is_hovered:
            painter.save()
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(self._selected_color if is_selected else self._hover_color))

            cell_rect = option.rect.adjusted(0, 2, 0, -2)
            if col == 0:
                cell_rect.setLeft(cell_rect.left() + 4)
            if col == col_count - 1:
                cell_rect.setRight(cell_rect.right() - 4)

            if col == 0 and col == col_count - 1:
                painter.drawRoundedRect(cell_rect, 6, 6)
            elif col == 0:
                painter.setClipRect(cell_rect)
                painter.drawRoundedRect(cell_rect.adjusted(0, 0, 10, 0), 6, 6)
            elif col == col_count - 1:
                painter.setClipRect(cell_rect)
                painter.drawRoundedRect(cell_rect.adjusted(-10, 0, 0, 0), 6, 6)
            else:
                painter.drawRect(cell_rect)

            painter.restore()

        opt = QStyleOptionViewItem(option)
        opt.state &= ~QStyle.State_Selected
        opt.state &= ~QStyle.State_MouseOver
        super().paint(painter, opt, index)


class CommanderTableDelegate(RowBackgroundDelegate):
    _D = 26   # diamètre des cercles
    _SP = 6   # espacement

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        super().paint(painter, option, index)

        if index.column() != 1:
            return

        colors = index.data(Qt.UserRole + 1)
        if not colors:
            return

        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)

        r = self._D / 2
        x = option.rect.left() + 14
        cy = option.rect.center().y()

        font = QFont()
        font.setPixelSize(14)
        painter.setFont(font)

        for code in colors:
            rect = QRectF(x, cy - r, self._D, self._D)

            painter.setBrush(QBrush(QColor(COLOR_HEX[code])))
            painter.setPen(QPen(QColor(0, 0, 0, 90), 1.5))
            painter.drawEllipse(rect)

            text_color = QColor("#1a1a1a") if code == "W" else QColor("#ffffff")
            painter.setPen(text_color)
            painter.drawText(rect, Qt.AlignCenter, COLOR_SYMBOLS[code])

            x += self._D + self._SP

        painter.restore()


class CommandersViewMain(QWidget):
    """Vue principale — liste des commandants jouables."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("PlayersViewMain")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._commanders: list[Commander] = []
        self._next_id = 1
        self._search_text: str = ""

        self._build_ui()
        self._load_commanders()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        layout.addWidget(self._build_header())
        self.table = self._build_table()
        layout.addWidget(self.table, 1)

    def _build_header(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("PlayersHeader")

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("👑 Commandants")
        title.setObjectName("SectionTitle")

        self.count_label = QLabel("")
        self.count_label.setObjectName("CountLabel")

        self.search_input = QLineEdit()
        self.search_input.setObjectName("PlayersSearchInput")
        self.search_input.setPlaceholderText("🔍 Rechercher un commandant…")
        self.search_input.setFixedWidth(260)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_search_changed)

        add_btn = QPushButton("➕ Ajouter un commandant")
        add_btn.setObjectName("PrimaryButton")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._add_commander)

        layout.addWidget(title)
        layout.addWidget(self.count_label)
        layout.addStretch()
        layout.addWidget(self.search_input)
        layout.addWidget(add_btn)

        return frame

    def _build_table(self) -> QTableWidget:
        table = QTableWidget()
        table.setObjectName("PlayersTable")

        columns = ["Nom du commandant", "Couleurs"]
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)

        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setAlternatingRowColors(False)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setFrameShape(QFrame.NoFrame)
        table.verticalHeader().setDefaultSectionSize(44)

        palette = table.palette()
        palette.setColor(QPalette.Base, QColor("#0f241d"))
        palette.setColor(QPalette.Highlight, QColor("#0f241d"))
        palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        table.setPalette(palette)
        table.viewport().setAutoFillBackground(True)

        table.setItemDelegate(CommanderTableDelegate(table))
        table.setMouseTracking(True)
        table.viewport().setMouseTracking(True)

        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Fixed)
        table.setColumnWidth(1, 170)

        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(self._show_context_menu)
        table.doubleClicked.connect(self._edit_selected)

        QShortcut(QKeySequence(Qt.Key_Delete), table).activated.connect(self._delete_selected)

        return table

    def _load_commanders(self):
        raw = CommanderStorage.load()
        self._commanders = [Commander.from_dict(d) for d in raw]
        if self._commanders:
            self._next_id = max(c.id for c in self._commanders) + 1
        self._refresh_table()

    def _save_commanders(self):
        CommanderStorage.save([c.to_dict() for c in self._commanders])

    def _on_search_changed(self, text: str):
        self._search_text = text.strip().lower()
        self._refresh_table()

    def _refresh_table(self):
        self._commanders.sort(key=lambda c: c.name.lower())

        filtered = self._commanders
        if self._search_text:
            filtered = [c for c in self._commanders if self._search_text in c.name.lower()]

        self.table.setRowCount(len(filtered))
        for row, commander in enumerate(filtered):
            self._set_row(row, commander)

        total = len(self._commanders)
        shown = len(filtered)
        if self._search_text and shown < total:
            self.count_label.setText(f"({shown}/{total})")
        else:
            self.count_label.setText(f"({total})" if total > 0 else "")

    def refresh(self):
        self._load_commanders()

    def _format_colors(self, commander: Commander) -> str:
        """Formate les couleurs pour l'affichage dans le tableau."""
        if commander.is_colorless:
            return "Incolore"
        return "  ".join(
            f"{COLOR_SYMBOLS[c]} {COLOR_LABELS[c]}"
            for c in MTG_COLORS
            if c in commander.colors
        )

    def _set_row(self, row: int, commander: Commander):
        name_item = QTableWidgetItem(commander.name)
        name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
        name_item.setData(Qt.UserRole, commander.id)
        self.table.setItem(row, 0, name_item)

        if commander.is_colorless:
            colors_item = QTableWidgetItem("Incolore")
        else:
            colors_item = QTableWidgetItem("")
            colors_item.setData(Qt.UserRole + 1, [c for c in MTG_COLORS if c in commander.colors])
        colors_item.setFlags(colors_item.flags() & ~Qt.ItemIsEditable)
        self.table.setItem(row, 1, colors_item)

    def _get_existing_names(self) -> list[str]:
        return [c.name for c in self._commanders]

    def _add_commander(self):
        dialog = CreateCommanderDialog(self, existing_names=self._get_existing_names())
        if not dialog.exec():
            return

        data = dialog.get_data()
        commander = Commander(id=self._next_id, name=data["name"], colors=data["colors"])
        self._next_id += 1
        self._commanders.append(commander)
        self._save_commanders()
        self._refresh_table()

    def _get_selected_commander(self) -> Commander | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if not item:
            return None
        commander_id = item.data(Qt.UserRole)
        return next((c for c in self._commanders if c.id == commander_id), None)

    def _edit_selected(self):
        commander = self._get_selected_commander()
        if not commander:
            return

        dialog = CreateCommanderDialog(
            self,
            commander=commander,
            existing_names=self._get_existing_names(),
        )
        if not dialog.exec():
            return

        dialog.apply_changes()
        self._save_commanders()
        self._refresh_table()

    def _delete_selected(self):
        commander = self._get_selected_commander()
        if not commander:
            return

        reply = QMessageBox.question(
            self,
            "Supprimer le commandant",
            f"Supprimer définitivement « {commander.name} » ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        self._commanders = [c for c in self._commanders if c.id != commander.id]
        self._save_commanders()
        self._refresh_table()

    def _show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return

        menu = QMenu(self)
        edit_action = menu.addAction("✏️ Modifier")
        menu.addSeparator()
        delete_action = menu.addAction("🗑️ Supprimer")

        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == edit_action:
            self._edit_selected()
        elif action == delete_action:
            self._delete_selected()
