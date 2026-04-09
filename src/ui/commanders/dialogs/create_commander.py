import json
import shutil
import threading
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QEvent, QPoint, Signal
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QFormLayout,
    QFileDialog,
    QMessageBox,
)

from core.commander import Commander, MTG_COLORS, COLOR_LABELS, COLOR_SYMBOLS, COLOR_HEX
from storage.base import DATA_DIR


class CreateCommanderDialog(QDialog):
    """Dialog pour créer ou éditer un commandant."""

    _suggestions_ready = Signal(list)

    def __init__(
        self,
        parent=None,
        commander: Commander | None = None,
        existing_names: list[str] | None = None,
    ):
        super().__init__(parent)

        self._commander = commander
        self._is_edit = commander is not None
        self._existing_names = [n.lower() for n in (existing_names or [])]
        self._image_path: str | None = None

        if self._is_edit and commander:
            self._existing_names = [
                n for n in self._existing_names if n != commander.name.lower()
            ]

        self.setWindowTitle("Modifier le commandant" if self._is_edit else "Nouveau commandant")
        self.setModal(True)
        self.setFixedSize(420, 400)
        self.setObjectName("CreatePlayerDialog")

        self.setAttribute(Qt.WA_TranslucentBackground, False)
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor("#0f241d"))
        self.setPalette(palette)

        self._color_checkboxes: dict[str, QPushButton] = {}

        self._build_ui()
        self._setup_autocomplete()
        self._load_data()

    def _setup_autocomplete(self):
        self._ac_timer = QTimer(self)
        self._ac_timer.setSingleShot(True)
        self._ac_timer.setInterval(350)
        self._ac_timer.timeout.connect(self._do_autocomplete)
        self._ac_query = ""

        self._dropdown = QListWidget(self)
        self._dropdown.setObjectName("ScryfallDropdown")
        self._dropdown.setFocusPolicy(Qt.NoFocus)
        self._dropdown.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._dropdown.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._dropdown.hide()
        self._dropdown.itemClicked.connect(self._on_suggestion_clicked)

        self._suggestions_ready.connect(self._show_dropdown)
        self.name_input.textEdited.connect(self._on_name_edited)
        self.name_input.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.name_input:
            if event.type() == QEvent.FocusOut:
                QTimer.singleShot(150, self._dropdown.hide)
            elif event.type() == QEvent.KeyPress:
                if event.key() == Qt.Key_Escape:
                    self._dropdown.hide()
                elif event.key() == Qt.Key_Down and self._dropdown.isVisible():
                    self._dropdown.setFocus()
                    self._dropdown.setCurrentRow(0)
                    return True
        return super().eventFilter(obj, event)

    def _on_name_edited(self, text: str):
        if len(text.strip()) >= 2:
            self._ac_timer.start()
        else:
            self._ac_timer.stop()
            self._ac_query = ""
            self._dropdown.hide()

    def _do_autocomplete(self):
        query = self.name_input.text().strip()
        if len(query) < 2:
            return
        self._ac_query = query

        # Lire les couleurs cochées dans le thread principal
        selected_colors = "".join(
            code for code, btn in self._color_checkboxes.items() if btn.isChecked()
        )
        color_filter = f" id>={selected_colors}" if selected_colors else ""

        def fetch(q: str, color_filter: str):
            try:
                # Filtre : créatures légendaires, véhicules légendaires,
                # et planeswalkers pouvant être commandant + couleurs sélectionnées
                encoded = urllib.parse.quote(f"{q} is:commander{color_filter}")
                req = urllib.request.Request(
                    f"https://api.scryfall.com/cards/search?q={encoded}&order=name&unique=cards",
                    headers={"User-Agent": "MagicTable/1.0", "Accept": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=4) as resp:
                    data = json.loads(resp.read().decode())
                names = [card["name"] for card in data.get("data", [])]
            except urllib.error.HTTPError:
                # 404 = aucun résultat, autres codes = erreur réseau
                names = []
            except Exception:
                names = []
            # Only emit if the query is still current (avoids stale responses)
            if self._ac_query == q:
                self._suggestions_ready.emit(names)

        threading.Thread(target=fetch, args=(query, color_filter), daemon=True).start()

    def _show_dropdown(self, names: list):
        if not names:
            self._dropdown.hide()
            return
        if not self.isVisible():
            return
        self._dropdown.clear()
        for name in names[:8]:
            self._dropdown.addItem(name)
        # Recompute position every time (layout may have shifted)
        pos = self.name_input.mapTo(self, QPoint(0, self.name_input.height() + 2))
        w = self.name_input.width()
        h = min(len(names), 8) * 30 + 4
        self._dropdown.setGeometry(pos.x(), pos.y(), w, h)
        self._dropdown.raise_()
        self._dropdown.show()

    def _on_suggestion_clicked(self, item: QListWidgetItem):
        self.name_input.setText(item.text())
        self._dropdown.hide()
        self._ac_timer.stop()
        self._clear_error()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 20, 24, 20)

        # Titre
        title = QLabel("✏️ Modifier le commandant" if self._is_edit else "➕ Nouveau commandant")
        title.setObjectName("DialogTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Nom
        form = QFormLayout()
        form.setSpacing(8)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Ex : Atraxa, Praetors' Voice")
        self.name_input.setObjectName("DialogInput")
        self.name_input.textChanged.connect(self._clear_error)
        self.name_input.returnPressed.connect(self._validate_and_accept)
        form.addRow("Nom *", self.name_input)

        self.error_label = QLabel("")
        self.error_label.setObjectName("ErrorLabel")
        self.error_label.hide()
        form.addRow("", self.error_label)

        layout.addLayout(form)

        # Couleurs
        colors_label = QLabel("Couleurs")
        colors_label.setObjectName("StatsLabel")
        layout.addWidget(colors_label)

        colors_row = QHBoxLayout()
        colors_row.setSpacing(10)
        colors_row.setAlignment(Qt.AlignCenter)

        for code in MTG_COLORS:
            btn = QPushButton(COLOR_SYMBOLS[code])
            btn.setCheckable(True)
            btn.setObjectName("ColorToggleButton")
            btn.setFixedSize(38, 38)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(COLOR_LABELS[code])
            btn.setProperty("colorCode", code)
            btn.setStyleSheet(self._get_color_btn_style(code, False))
            btn.toggled.connect(lambda checked, b=btn, c=code: self._on_color_toggled(b, c, checked))

            self._color_checkboxes[code] = btn
            colors_row.addWidget(btn)

        layout.addLayout(colors_row)

        self.colorless_label = QLabel("Incolore")
        self.colorless_label.setObjectName("StatsLabel")
        self.colorless_label.hide()
        layout.addWidget(self.colorless_label)

        # Duel Commander
        self._duel_check = QCheckBox("⚔️  Duel Commander")
        self._duel_check.setObjectName("DuelCheckbox")
        self._duel_check.setStyleSheet(
            "QCheckBox { color: #7a9a8a; font-size: 12px; spacing: 6px; }"
            "QCheckBox::indicator { width: 14px; height: 14px; border: 1px solid #3a5a4a;"
            "  border-radius: 3px; background: #0f241d; }"
            "QCheckBox::indicator:checked { background: #2d8a5e; border-color: #3fd27d; }"
        )
        layout.addWidget(self._duel_check)

        # Image
        image_section_label = QLabel("Image de fond")
        image_section_label.setObjectName("StatsLabel")
        layout.addWidget(image_section_label)

        image_row = QHBoxLayout()
        image_row.setSpacing(8)

        self._image_indicator = QLabel("●")
        self._image_indicator.setObjectName("ImageIndicator")
        self._image_indicator.setFixedSize(20, 30)
        self._image_indicator.setAlignment(Qt.AlignCenter)
        self._image_indicator.setStyleSheet("color: #3a5a4a; font-size: 14px;")

        choose_btn = QPushButton("📁 Choisir…")
        choose_btn.setObjectName("ImagePickerButton")
        choose_btn.setFixedHeight(30)
        choose_btn.setCursor(Qt.PointingHandCursor)
        choose_btn.clicked.connect(self._pick_image)

        self._scryfall_btn = QPushButton("🔍 Scryfall")
        self._scryfall_btn.setObjectName("ImagePickerButton")
        self._scryfall_btn.setFixedHeight(30)
        self._scryfall_btn.setCursor(Qt.PointingHandCursor)
        self._scryfall_btn.setToolTip("Télécharger l'art crop depuis Scryfall")
        self._scryfall_btn.clicked.connect(self._fetch_scryfall_image)

        self._clear_image_btn = QPushButton("✕")
        self._clear_image_btn.setObjectName("ImageClearButton")
        self._clear_image_btn.setFixedSize(30, 30)
        self._clear_image_btn.setCursor(Qt.PointingHandCursor)
        self._clear_image_btn.clicked.connect(self._clear_image)
        self._clear_image_btn.hide()

        image_row.addWidget(self._image_indicator)
        image_row.addWidget(choose_btn)
        image_row.addWidget(self._scryfall_btn)
        image_row.addWidget(self._clear_image_btn)
        layout.addLayout(image_row)

        layout.addStretch()

        # Boutons
        buttons = QHBoxLayout()
        buttons.setSpacing(12)

        cancel_btn = QPushButton("Annuler")
        cancel_btn.setObjectName("CancelButton")
        cancel_btn.clicked.connect(self.reject)

        self.save_btn = QPushButton("Enregistrer" if self._is_edit else "Créer")
        self.save_btn.setObjectName("PrimaryButton")
        self.save_btn.clicked.connect(self._validate_and_accept)

        buttons.addStretch()
        buttons.addWidget(cancel_btn)
        buttons.addWidget(self.save_btn)

        layout.addLayout(buttons)

        self.name_input.setFocus()

    # ------------------------------------------------------------------
    # Color buttons
    # ------------------------------------------------------------------

    def _get_color_btn_style(self, code: str, checked: bool) -> str:
        hex_color = COLOR_HEX[code]
        size = "min-width:38px;max-width:38px;min-height:38px;max-height:38px;padding:0px;"
        if checked:
            # Assombrir le fond pour faire ressortir le symbole
            bg = QColor(hex_color).darker(160).name() if code != "W" else hex_color
            text_color = "#2a1500" if code == "W" else "#ffffff"
            border = "#b8960a" if code == "W" else hex_color
            return (
                f"QPushButton {{"
                f"  {size}"
                f"  background-color: {bg};"
                f"  color: {text_color};"
                f"  border: 3px solid {border};"
                f"  border-radius: 19px;"
                f"  font-size: 18px;"
                f"}}"
                f"QPushButton:hover {{"
                f"  border: 3px solid {'rgba(184,150,10,1)' if code == 'W' else 'rgba(255,255,255,1)'};"
                f"}}"
            )
        else:
            return (
                f"QPushButton {{"
                f"  {size}"
                f"  background-color: #132f26;"
                f"  color: {hex_color};"
                f"  border: 2px solid {hex_color}99;"
                f"  border-radius: 19px;"
                f"  font-size: 18px;"
                f"}}"
                f"QPushButton:hover {{"
                f"  background-color: {hex_color}22;"
                f"  border: 2px solid {hex_color};"
                f"}}"
            )

    def _on_color_toggled(self, btn: QPushButton, code: str, checked: bool):
        btn.setStyleSheet(self._get_color_btn_style(code, checked))
        any_checked = any(b.isChecked() for b in self._color_checkboxes.values())
        self.colorless_label.setVisible(not any_checked)
        # Relancer l'autocomplétion si le champ est assez rempli
        if len(self.name_input.text().strip()) >= 2:
            self._ac_timer.start()

    # ------------------------------------------------------------------
    # Image
    # ------------------------------------------------------------------

    def _fetch_scryfall_image(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Nom requis", "Entrez d'abord le nom du commandant.")
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        self._scryfall_btn.setEnabled(False)
        try:
            # Recherche sur l'API Scryfall
            encoded = urllib.parse.quote(name)
            req = urllib.request.Request(
                f"https://api.scryfall.com/cards/named?fuzzy={encoded}",
                headers={"User-Agent": "MagicTable/1.0", "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                card = json.loads(resp.read().decode("utf-8"))

            # Récupérer l'URL art_crop (cartes double face : première face)
            image_uris = card.get("image_uris") or {}
            if not image_uris:
                faces = card.get("card_faces", [])
                if faces:
                    image_uris = faces[0].get("image_uris", {})

            art_url = image_uris.get("art_crop")
            if not art_url:
                QMessageBox.warning(self, "Image introuvable",
                                    f"Aucune image disponible pour « {card.get('name', name)} ».")
                return

            # Téléchargement
            dest_dir = DATA_DIR / "commander_images"
            dest_dir.mkdir(exist_ok=True)
            filename = f"{uuid.uuid4().hex}.jpg"

            img_req = urllib.request.Request(
                art_url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
            )
            with urllib.request.urlopen(img_req, timeout=15) as img_resp:
                (dest_dir / filename).write_bytes(img_resp.read())

            self._image_path = f"commander_images/{filename}"
            self._update_image_ui()

        except urllib.error.HTTPError as e:
            if e.code == 404:
                QMessageBox.warning(self, "Introuvable",
                                    f"« {name} » introuvable sur Scryfall.\n"
                                    "Vérifiez l'orthographe ou utilisez le nom anglais.")
            else:
                QMessageBox.warning(self, "Erreur réseau", f"Erreur HTTP {e.code}.")
        except urllib.error.URLError as e:
            QMessageBox.warning(self, "Erreur réseau",
                                f"Impossible de joindre Scryfall :\n{e.reason}")
        except Exception as e:
            QMessageBox.warning(self, "Erreur", str(e))
        finally:
            QApplication.restoreOverrideCursor()
            self._scryfall_btn.setEnabled(True)

    def _pick_image(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Choisir une image", "",
            "Images (*.png *.jpg *.jpeg *.webp)"
        )
        if not path:
            return

        dest_dir = DATA_DIR / "commander_images"
        dest_dir.mkdir(exist_ok=True)
        ext = Path(path).suffix.lower()
        filename = f"{uuid.uuid4().hex}{ext}"
        shutil.copy2(path, dest_dir / filename)

        self._image_path = f"commander_images/{filename}"
        self._update_image_ui()

    def _clear_image(self):
        self._image_path = None
        self._update_image_ui()

    def _update_image_ui(self):
        if self._image_path:
            self._image_indicator.setStyleSheet("color: #3ad68a; font-size: 14px;")
            self._image_indicator.setToolTip("Image chargée")
            self._clear_image_btn.show()
        else:
            self._image_indicator.setStyleSheet("color: #3a5a4a; font-size: 14px;")
            self._image_indicator.setToolTip("Aucune image")
            self._clear_image_btn.hide()

    # ------------------------------------------------------------------
    # Load / validate / get
    # ------------------------------------------------------------------

    def _load_data(self):
        if not self._commander:
            return
        self.name_input.setText(self._commander.name)
        for code, btn in self._color_checkboxes.items():
            btn.setChecked(code in self._commander.colors)
        self._image_path = self._commander.image_path
        self._update_image_ui()
        self._duel_check.setChecked(self._commander.duel)

    def _clear_error(self):
        self.error_label.hide()
        self.name_input.setProperty("error", False)
        self.name_input.style().unpolish(self.name_input)
        self.name_input.style().polish(self.name_input)

    def _show_error(self, message: str):
        self.error_label.setText(message)
        self.error_label.show()
        self.name_input.setProperty("error", True)
        self.name_input.style().unpolish(self.name_input)
        self.name_input.style().polish(self.name_input)
        self.name_input.setFocus()

    def _validate_and_accept(self):
        name = self.name_input.text().strip()
        if not name:
            self._show_error("Le nom est requis")
            return
        if name.lower() in self._existing_names:
            self._show_error("Ce commandant existe déjà")
            return
        self.accept()

    def get_data(self) -> dict:
        colors = [code for code, btn in self._color_checkboxes.items() if btn.isChecked()]
        return {
            "name": self.name_input.text().strip(),
            "colors": colors,
            "image_path": self._image_path,
            "duel": self._duel_check.isChecked(),
        }

    def apply_changes(self):
        if not self._commander:
            return
        data = self.get_data()
        self._commander.name = data["name"]
        self._commander.colors = data["colors"]
        self._commander.image_path = data["image_path"]
        self._commander.duel = data["duel"]
