from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QScrollArea,
    QMessageBox,
    QMenu,
    QLineEdit,
)

from core.commander import Commander
from storage.commanders import CommanderStorage
from ui.commanders.commander_card import CommanderCard
from ui.commanders.dialogs.create_commander import CreateCommanderDialog
from ui.commanders.dialogs.commander_stats import CommanderStatsDialog
from ui.widgets.flow_layout import FlowLayout


class CommandersViewMain(QWidget):
    """Vue principale — grille de tuiles des commandants jouables."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("PlayersViewMain")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._commanders: list[Commander] = []
        self._next_id = 1
        self._search_text: str = ""
        self._selected_id: int | None = None

        self._build_ui()
        self._load_commanders()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        layout.addWidget(self._build_header())
        layout.addWidget(self._build_grid(), 1)

        QShortcut(QKeySequence(Qt.Key_Delete), self).activated.connect(self._delete_selected)

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

    def _build_grid(self) -> QScrollArea:
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setObjectName("CommanderGridScroll")

        self._grid_content = QWidget()
        self._grid_content.setObjectName("CommanderGridContent")
        self._flow = FlowLayout(self._grid_content, h_spacing=16, v_spacing=16)
        self._flow.setContentsMargins(4, 4, 4, 4)
        self._scroll.setWidget(self._grid_content)
        return self._scroll

    # ------------------------------------------------------------------
    # Data
    # ------------------------------------------------------------------

    def _load_commanders(self):
        raw = CommanderStorage.load()
        self._commanders = [Commander.from_dict(d) for d in raw]
        if self._commanders:
            self._next_id = max(c.id for c in self._commanders) + 1
        self._refresh_grid()

    def _save_commanders(self):
        CommanderStorage.save([c.to_dict() for c in self._commanders])

    def refresh(self):
        self._load_commanders()

    # ------------------------------------------------------------------
    # Grid
    # ------------------------------------------------------------------

    def _on_search_changed(self, text: str):
        self._search_text = text.strip().lower()
        self._refresh_grid()

    def _refresh_grid(self):
        while self._flow.count():
            item = self._flow.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        self._commanders.sort(key=lambda c: c.name.lower())
        filtered = self._commanders
        if self._search_text:
            filtered = [c for c in self._commanders if self._search_text in c.name.lower()]

        for commander in filtered:
            card = CommanderCard(commander, selected=self._selected_id == commander.id)
            card.clicked.connect(self._on_card_clicked)
            card.double_clicked.connect(self._on_card_double_clicked)
            card.context_menu_requested.connect(self._on_card_context_menu)
            self._flow.addWidget(card)

        total = len(self._commanders)
        shown = len(filtered)
        if self._search_text and shown < total:
            self.count_label.setText(f"({shown}/{total})")
        else:
            self.count_label.setText(f"({total})" if total > 0 else "")

    def _update_card_selection(self):
        for i in range(self._flow.count()):
            item = self._flow.itemAt(i)
            if item and item.widget():
                card: CommanderCard = item.widget()
                card.set_selected(card.commander_id == self._selected_id)

    # ------------------------------------------------------------------
    # Card signals
    # ------------------------------------------------------------------

    def _on_card_clicked(self, commander_id: int):
        self._selected_id = commander_id
        self._update_card_selection()

    def _on_card_double_clicked(self, commander_id: int):
        self._selected_id = commander_id
        commander = self._get_selected_commander()
        if commander:
            CommanderStatsDialog(commander, self).exec()

    def _on_card_context_menu(self, commander_id: int, pos: QPoint):
        self._selected_id = commander_id
        self._update_card_selection()

        menu = QMenu(self)
        edit_action = menu.addAction("✏️ Modifier")
        menu.addSeparator()
        delete_action = menu.addAction("🗑️ Supprimer")

        action = menu.exec(pos)
        if action == edit_action:
            self._edit_selected()
        elif action == delete_action:
            self._delete_selected()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def _get_existing_names(self) -> list[str]:
        return [c.name for c in self._commanders]

    def _get_selected_commander(self) -> Commander | None:
        if self._selected_id is None:
            return None
        return next((c for c in self._commanders if c.id == self._selected_id), None)

    def _add_commander(self):
        dialog = CreateCommanderDialog(self, existing_names=self._get_existing_names())
        if not dialog.exec():
            return

        data = dialog.get_data()
        commander = Commander(
            id=self._next_id,
            name=data["name"],
            colors=data["colors"],
            image_path=data.get("image_path"),
        )
        self._next_id += 1
        self._commanders.append(commander)
        self._save_commanders()
        self._refresh_grid()

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
        self._refresh_grid()

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
        self._selected_id = None
        self._save_commanders()
        self._refresh_grid()
