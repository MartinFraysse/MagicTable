from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QGridLayout, QMenu, QMessageBox,
    QSizePolicy,
)
from PySide6.QtGui import QKeySequence, QShortcut

from core.commander import Commander
from core.theme_manager import theme_manager
from storage.commanders import CommanderStorage
from ui.commanders.dialogs.create_commander import CreateCommanderDialog


# ── Couleurs ──────────────────────────────────────────────────────────────────

_PIP_STYLE = {
    "W": ("background:#e8e4cc; color:#333333;",),
    "U": ("background:#2e6ec0; color:#ffffff;",),
    "B": ("background:#1a1a2e; color:#bbbbbb; border:1px solid #444;",),
    "R": ("background:#c0392b; color:#ffffff;",),
    "G": ("background:#1e7a40; color:#ffffff;",),
}

_BADGE_STYLE = {
    "commander": "background:rgba(58,214,138,0.18); color:#3ad68a; border:1px solid rgba(58,214,138,0.4);",
    "duel":      "background:rgba(91,160,224,0.18); color:#5ba0e0; border:1px solid rgba(91,160,224,0.4);",
    "both":      "background:rgba(168,127,220,0.18); color:#a87fdc; border:1px solid rgba(168,127,220,0.4);",
}

_CARD_DARK = {
    "bg":      "qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #184a39,stop:1 #0f2f25)",
    "border":  "#2a5e45",
    "name":    "#eafff6",
    "none":    "#4a6e5a",
}

_CARD_LIGHT = {
    "bg":      "qlineargradient(x1:0,y1:0,x2:0,y2:1,stop:0 #ffffff,stop:1 #f0faf7)",
    "border":  "#c0e0d5",
    "name":    "#1a3d33",
    "none":    "#8ab0a0",
}


# ── Carte commandant ──────────────────────────────────────────────────────────

class _CommanderCard(QFrame):
    edit_requested   = Signal()
    delete_requested = Signal()

    def __init__(self, commander: Commander, is_dark: bool, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setCursor(Qt.PointingHandCursor)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_menu)
        self._cmd = commander

        c = _CARD_DARK if is_dark else _CARD_LIGHT
        self.setStyleSheet(f"""
            QFrame {{
                background: {c['bg']};
                border: 1px solid {c['border']};
                border-radius: 12px;
            }}
            QFrame:hover {{
                border-color: rgba(58,214,138,0.65);
            }}
            QLabel#CardName {{
                color: {c['name']};
                font-size: 14px;
                font-weight: 700;
                background: transparent;
                border: none;
            }}
            QLabel#CardNone {{
                color: {c['none']};
                font-size: 11px;
                font-style: italic;
                background: transparent;
                border: none;
            }}
        """)
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        # Nom
        name = QLabel(self._cmd.name)
        name.setObjectName("CardName")
        name.setWordWrap(True)
        layout.addWidget(name)

        # Ligne du bas : pips à gauche, badge à droite
        bottom = QHBoxLayout()
        bottom.setSpacing(6)
        bottom.setContentsMargins(0, 0, 0, 0)

        # Pips de couleur
        if self._cmd.colors:
            for c in self._cmd.colors.upper():
                if c in _PIP_STYLE:
                    pip = QLabel(c)
                    pip.setAlignment(Qt.AlignCenter)
                    pip.setFixedSize(20, 20)
                    style = _PIP_STYLE[c][0]
                    pip.setStyleSheet(
                        f"QLabel {{ {style} border-radius:10px; font-size:9px; font-weight:800; }}"
                    )
                    bottom.addWidget(pip)
        else:
            none_lbl = QLabel("Incolore")
            none_lbl.setObjectName("CardNone")
            bottom.addWidget(none_lbl)

        bottom.addStretch()

        # Badge format aligné à droite
        badge_style = _BADGE_STYLE.get(self._cmd.format, "")
        badge = QLabel(self._cmd.format_label)
        badge.setStyleSheet(
            f"QLabel {{ {badge_style} border-radius:5px; padding:2px 8px;"
            f" font-size:10px; font-weight:600; }}"
        )
        badge.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
        bottom.addWidget(badge)

        layout.addLayout(bottom)

    def mouseDoubleClickEvent(self, event):
        self.edit_requested.emit()
        super().mouseDoubleClickEvent(event)

    def _show_menu(self, pos):
        menu = QMenu(self)
        edit_action   = menu.addAction("✏️ Modifier")
        menu.addSeparator()
        delete_action = menu.addAction("🗑️ Supprimer")
        action = menu.exec(self.mapToGlobal(pos))
        if action == edit_action:
            self.edit_requested.emit()
        elif action == delete_action:
            self.delete_requested.emit()


# ── Vue principale ────────────────────────────────────────────────────────────

class CommandersViewMain(QWidget):
    _COLS = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("CommandersViewMain")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._commanders: list[Commander] = []
        self._next_id = 1

        self._build_ui()
        self._load()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        outer.setSpacing(20)
        outer.addWidget(self._build_header())

        scroll = QScrollArea()
        scroll.setObjectName("CommandersScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        self._content = QWidget()
        self._content.setObjectName("CommandersContent")
        self._content.setAttribute(Qt.WA_StyledBackground, True)

        self._grid = QGridLayout(self._content)
        self._grid.setContentsMargins(0, 0, 0, 0)
        self._grid.setSpacing(16)
        for col in range(self._COLS):
            self._grid.setColumnStretch(col, 1)

        scroll.setWidget(self._content)
        outer.addWidget(scroll, 1)

    def _build_header(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("CommandersHeader")

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("🧙 Commandants")
        title.setObjectName("SectionTitle")

        self._count_label = QLabel("")
        self._count_label.setObjectName("CountLabel")

        add_btn = QPushButton("➕ Ajouter un commandant")
        add_btn.setObjectName("PrimaryButton")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._add)

        layout.addWidget(title)
        layout.addWidget(self._count_label)
        layout.addStretch()
        layout.addWidget(add_btn)
        return frame

    # ── Storage ───────────────────────────────────────────────────────────────

    def _load(self):
        raw = CommanderStorage.load()
        self._commanders = [Commander.from_dict(d) for d in raw]
        if self._commanders:
            self._next_id = max(c.id for c in self._commanders) + 1
        self._refresh_grid()

    def _save(self):
        CommanderStorage.save([c.to_dict() for c in self._commanders])

    def refresh(self):
        self._load()

    # ── Grille ────────────────────────────────────────────────────────────────

    def _clear_grid(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _refresh_grid(self):
        self._clear_grid()
        self._commanders.sort(key=lambda c: c.name.lower())

        count = len(self._commanders)
        self._count_label.setText(f"({count})" if count else "")

        is_dark = theme_manager.get_theme() == "dark"

        if not self._commanders:
            empty = QLabel("Aucun commandant enregistré.\nCliquez sur « Ajouter un commandant » pour commencer.")
            empty.setObjectName("CommandersEmptyState")
            empty.setAlignment(Qt.AlignCenter)
            self._grid.addWidget(empty, 0, 0, 1, self._COLS)
            self._grid.setRowStretch(1, 1)
            return

        for i, cmd in enumerate(self._commanders):
            row, col = divmod(i, self._COLS)
            card = _CommanderCard(cmd, is_dark, self)
            card.edit_requested.connect(lambda c=cmd: self._edit(c))
            card.delete_requested.connect(lambda c=cmd: self._delete(c))
            self._grid.addWidget(card, row, col)

        last_row = (count - 1) // self._COLS + 1
        self._grid.setRowStretch(last_row, 1)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _existing_names(self) -> list[str]:
        return [c.name for c in self._commanders]

    def _add(self):
        dialog = CreateCommanderDialog(self, existing_names=self._existing_names())
        if not dialog.exec():
            return
        data = dialog.get_data()
        cmd = Commander(id=self._next_id, **data)
        self._next_id += 1
        self._commanders.append(cmd)
        self._save()
        self._refresh_grid()

    def _edit(self, cmd: Commander):
        dialog = CreateCommanderDialog(self, commander=cmd, existing_names=self._existing_names())
        if not dialog.exec():
            return
        dialog.apply_changes()
        self._save()
        self._refresh_grid()

    def _delete(self, cmd: Commander):
        reply = QMessageBox.question(
            self,
            "Supprimer le commandant",
            f"Supprimer définitivement « {cmd.name} » ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._commanders = [c for c in self._commanders if c.id != cmd.id]
        self._save()
        self._refresh_grid()
