from PySide6.QtCore import Qt, Signal, QRect, QModelIndex, QEvent
from PySide6.QtGui import QPainter, QBrush, QColor
from PySide6.QtWidgets import (
    QWidget,
    QDialog,
    QListWidgetItem,
    QLineEdit,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QGridLayout,
    QListWidget,
    QMessageBox,
    QMenu,
    QCompleter,
    QInputDialog,
    QStyledItemDelegate,
    QStyleOptionViewItem,
    QStyle,
)
import json

from core.tournament import Tournament
from core.regular_player import RegularPlayer
from core.swiss_pairing import compute_recommended_rounds
from storage.tournaments import TournamentStorage
from storage.regular_players import RegularPlayerStorage
from ui.tournaments.dialogs.edit_player import EditPlayerDialog


class PlayerListDelegate(QStyledItemDelegate):
    """Delegate pour dessiner un fond arrondi sur les items de la liste."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hover_color = QColor(63, 210, 125, 38)
        self._selected_color = QColor(63, 210, 125, 77)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        is_selected = bool(option.state & QStyle.State_Selected)
        is_hovered = bool(option.state & QStyle.State_MouseOver)

        if is_selected or is_hovered:
            painter.save()
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.NoPen)

            # Rectangle avec marges
            item_rect = QRect(
                option.rect.left() + 4,
                option.rect.top() + 2,
                option.rect.width() - 8,
                option.rect.height() - 4
            )

            if is_selected:
                painter.setBrush(QBrush(self._selected_color))
            else:
                painter.setBrush(QBrush(self._hover_color))

            painter.drawRoundedRect(item_rect, 6, 6)
            painter.restore()

        # Dessiner le contenu normal
        super().paint(painter, option, index)


class BrowsePlayersDialog(QDialog):
    """Dialog pour parcourir et ajouter directement des joueurs permanents au tournoi."""

    def __init__(self, parent, regular_players: list, tournament):
        super().__init__(parent)
        self.setWindowTitle("Joueurs permanents")
        self.setModal(True)
        self.setObjectName("BrowsePlayersDialog")
        self.setMinimumWidth(280)
        self.setMinimumHeight(400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._regular_players = sorted(regular_players, key=lambda p: p.pseudo.lower())
        self._tournament = tournament

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 14)

        # ── Titre ─────────────────────────────────────────────────────
        title = QLabel("👥 Joueurs permanents")
        title.setObjectName("LaunchSectionTitle")
        layout.addWidget(title)

        # ── Filtre ────────────────────────────────────────────────────
        self.filter_input = QLineEdit()
        self.filter_input.setObjectName("LaunchPlayerInput")
        self.filter_input.setPlaceholderText("Filtrer…")
        self.filter_input.textChanged.connect(self._refresh_list)
        layout.addWidget(self.filter_input)

        # ── Liste ─────────────────────────────────────────────────────
        self.list_widget = QListWidget()
        self.list_widget.setObjectName("LaunchPlayersList")
        self.list_widget.setSpacing(2)
        self.list_widget.setMouseTracking(True)
        self.list_widget.viewport().setMouseTracking(True)
        self.list_widget.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self.list_widget, 1)

        hint = QLabel("Cliquer pour ajouter  •  ✔ déjà inscrit")
        hint.setObjectName("BracketRoundSubtitle")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

        # ── Fermer ────────────────────────────────────────────────────
        close_btn = QPushButton("Fermer")
        close_btn.setObjectName("BracketCancelButton")
        close_btn.setFixedHeight(28)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignCenter)

        self._refresh_list()

    def _in_tournament(self) -> dict:
        """Retourne {nom_lowercase: player_id} pour les joueurs inscrits."""
        return {p.name.lower().strip(): p.id for p in self._tournament.players}

    def _refresh_list(self):
        f = self.filter_input.text().lower().strip()
        in_t = self._in_tournament()

        self.list_widget.clear()
        for player in self._regular_players:
            if f and f not in player.pseudo.lower():
                continue
            player_id = in_t.get(player.pseudo.lower().strip())
            already = player_id is not None
            if already:
                item = QListWidgetItem(f"✔  {player.pseudo}")
                item.setForeground(QBrush(QColor(130, 130, 130)))
            else:
                item = QListWidgetItem(player.pseudo)
            # UserRole = pseudo, UserRole+1 = player_id si inscrit (None sinon)
            item.setData(Qt.UserRole, player.pseudo)
            item.setData(Qt.UserRole + 1, player_id)
            self.list_widget.addItem(item)

    def _on_item_clicked(self, item: QListWidgetItem):
        pseudo = item.data(Qt.UserRole)
        player_id = item.data(Qt.UserRole + 1)
        if player_id is not None:
            # Déjà inscrit → retirer du tournoi
            self._tournament.remove_player(player_id)
        else:
            # Pas encore inscrit → ajouter
            self._tournament.add_player(pseudo)
        self._refresh_list()

    def _add_player(self, name: str):
        self._tournament.add_player(name)
        self._refresh_list()


class LaunchView(QWidget):
    """
    Vue de lancement d’un tournoi.
    """

    # =====================
    # Signals
    # =====================
    tournament_taken = Signal(int)
    tournament_cancelled = Signal(int)
    edit_requested = Signal(Tournament)
    start_requested = Signal(Tournament)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._current_tournament: Tournament | None = None
        self._regular_players: list[RegularPlayer] = []
        self._completer_search_text: str = ""  # Texte original pour l'autocomplétion
        self._completer_current_row: int = -1  # Index courant dans le cycle Tab

        self.setObjectName("LaunchView")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAcceptDrops(True)

        self._load_regular_players()
        self._build_ui()

    # ======================================================
    # Regular Players (autocomplétion)
    # ======================================================
    def _load_regular_players(self):
        """Charge les joueurs réguliers pour l'autocomplétion."""
        raw = RegularPlayerStorage.load()
        self._regular_players = [RegularPlayer.from_dict(d) for d in raw]

    def _get_regular_player_pseudos(self) -> list[str]:
        """Retourne la liste des pseudos des joueurs réguliers."""
        return [p.pseudo for p in self._regular_players]

    def _setup_completer(self):
        """Configure l'autocomplétion sur le champ joueur."""
        pseudos = self._get_regular_player_pseudos()
        completer = QCompleter(pseudos, self)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.player_input.setCompleter(completer)
        # Installer le filtre sur le popup pour intercepter Tab/Enter
        # (quand le popup est visible, les events clavier lui sont envoyés, pas au champ)
        completer.popup().installEventFilter(self)

    def refresh_regular_players(self):
        """Rafraîchit la liste des joueurs réguliers (appelé après ajout)."""
        self._load_regular_players()
        self._setup_completer()

    # ======================================================
    # 🔑 HELPER — retrouver UpcomingView dans l'arbre Qt
    # ======================================================
    def _get_upcoming_view(self):
        parent = self.parent()
        while parent:
            if hasattr(parent, "upcoming_view"):
                return parent.upcoming_view
            parent = parent.parent()
        return None

    # ======================================================
    # UI
    # ======================================================
    def _build_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        # ==================================================
        # PLACEHOLDER
        # ==================================================
        self.placeholder_widget = QFrame()
        self.placeholder_widget.setObjectName("LaunchContainerInner")
        self.placeholder_widget.setAttribute(Qt.WA_StyledBackground, True)

        ph_layout = QVBoxLayout(self.placeholder_widget)
        ph_layout.setAlignment(Qt.AlignCenter)
        ph_layout.setSpacing(12)

        title = QLabel("🎮 Lancer un tournoi")
        title.setObjectName("LaunchTitle")
        title.setAlignment(Qt.AlignCenter)

        subtitle = QLabel(
            "Sélectionnez ou déposez un tournoi\n"
            "depuis la liste des tournois à venir"
        )
        subtitle.setObjectName("LaunchSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)

        ph_layout.addWidget(title)
        ph_layout.addWidget(subtitle)

        # ==================================================
        # CARD CONTAINER
        # ==================================================
        self.card_container = QFrame()
        self.card_container.setObjectName("LaunchCardContainer")
        self.card_container.setAttribute(Qt.WA_StyledBackground, True)
        self.card_container.hide()

        card_layout = QVBoxLayout(self.card_container)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # ==================================================
        # HEADER
        # ==================================================
        self.header_container = QFrame()
        self.header_container.setObjectName("LaunchHeaderContainer")
        self.header_container.setAttribute(Qt.WA_StyledBackground, True)

        header_layout = QGridLayout(self.header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setHorizontalSpacing(16)
        header_layout.setVerticalSpacing(6)

        self.header_title = QLabel()
        self.header_title.setObjectName("LaunchHeaderTitle")

        self.header_format = QLabel()
        self.header_format.setObjectName("LaunchHeaderFormat")

        self.header_meta = QLabel()
        self.header_meta.setObjectName("LaunchHeaderMeta")

        self.edit_btn = QPushButton("Modifier")
        self.edit_btn.setObjectName("LaunchPrimaryButton")
        self.edit_btn.clicked.connect(self._edit_current_tournament)

        self.cancel_btn = QPushButton("Retirer")
        self.cancel_btn.setObjectName("LaunchPrimaryButton")
        self.cancel_btn.clicked.connect(self._cancel_current_tournament)

        header_layout.addWidget(self.header_title, 0, 0)
        header_layout.addWidget(self.edit_btn, 0, 1)
        header_layout.addWidget(self.header_format, 1, 0)
        header_layout.addWidget(self.cancel_btn, 1, 1)
        header_layout.addWidget(self.header_meta, 2, 0, 1, 2)

        card_layout.addWidget(self.header_container)

        # ==================================================
        # BODY
        # ==================================================
        self.body_container = QFrame()
        self.body_container.setObjectName("LaunchPreparationContainer")
        self.body_container.setAttribute(Qt.WA_StyledBackground, True)

        body_layout = QVBoxLayout(self.body_container)
        body_layout.setContentsMargins(0, 0, 0, 0)

        self.prep_container = QFrame()
        self.prep_container.setObjectName("LaunchPreparationInner")

        prep_layout = QVBoxLayout(self.prep_container)
        prep_layout.setContentsMargins(0, 0, 0, 0)
        prep_layout.setSpacing(16)

        players_title = QLabel("👥 Joueurs inscrits")
        players_title.setObjectName("LaunchSectionTitle")
        prep_layout.addWidget(players_title)

        self.players_list = QListWidget()
        self.players_list.setObjectName("LaunchPlayersList")
        self.players_list.setSpacing(4)
        self.players_list.setUniformItemSizes(True)
        self.players_list.setSelectionMode(QListWidget.SingleSelection)
        self.players_list.setFocusPolicy(Qt.StrongFocus)
        self.players_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.players_list.customContextMenuRequested.connect(
            self._show_player_context_menu
        )
        self.players_list.itemDoubleClicked.connect(
            self._on_player_double_clicked
        )

        # Delegate pour fond arrondi unifié
        player_delegate = PlayerListDelegate(self.players_list)
        self.players_list.setItemDelegate(player_delegate)
        self.players_list.setMouseTracking(True)
        self.players_list.viewport().setMouseTracking(True)

        prep_layout.addWidget(self.players_list)

        row = QHBoxLayout()
        self.player_input = QLineEdit()
        self.player_input.setObjectName("LaunchPlayerInput")
        self.player_input.setPlaceholderText("Nom du joueur (autocomplétion disponible)")
        self.player_input.returnPressed.connect(self._add_player_manual)

        # Configurer l'autocomplétion et la rafraîchir au focus
        self._setup_completer()
        self.player_input.installEventFilter(self)

        add_btn = QPushButton("➕ Ajouter")
        add_btn.setObjectName("LaunchPrimaryButton")
        add_btn.clicked.connect(self._add_player_manual)

        browse_btn = QPushButton("👥")
        browse_btn.setObjectName("LaunchBrowseButton")
        browse_btn.setToolTip("Parcourir les joueurs permanents")
        browse_btn.setFixedHeight(32)
        browse_btn.setCursor(Qt.PointingHandCursor)
        browse_btn.clicked.connect(self._browse_regular_players)

        row.addWidget(self.player_input)
        row.addWidget(add_btn)
        row.addWidget(browse_btn)
        prep_layout.addLayout(row)

        self.reco_rounds_label = QLabel("")
        self.reco_rounds_label.setObjectName("LaunchRecoRoundsLabel")
        prep_layout.addWidget(self.reco_rounds_label)

        tables_row = QHBoxLayout()

        self.tables_info = QLabel()
        self.tables_info.setObjectName("LaunchInfoText")

        tables_row.addWidget(self.tables_info)
        tables_row.addStretch()

        start_col = QVBoxLayout()
        start_col.setSpacing(4)

        self.min_players_label = QLabel()
        self.min_players_label.setStyleSheet("color: #e94560; font-size: 12px;")
        self.min_players_label.setAlignment(Qt.AlignCenter)
        self.min_players_label.hide()

        self.start_btn = QPushButton("🚀 Lancer le tournoi")
        self.start_btn.setObjectName("LaunchPrimaryButton")
        self.start_btn.setMinimumHeight(56)
        self.start_btn.setMinimumWidth(220)
        self.start_btn.setEnabled(False)
        self.start_btn.clicked.connect(self._start_tournament)

        self.commander_warning = QLabel()
        self.commander_warning.setStyleSheet("color: #e94560; font-size: 12px;")
        self.commander_warning.setAlignment(Qt.AlignCenter)
        self.commander_warning.hide()

        start_col.addWidget(self.min_players_label)
        start_col.addWidget(self.start_btn)
        start_col.addWidget(self.commander_warning)

        tables_row.addLayout(start_col)

        prep_layout.addLayout(tables_row)

        body_layout.addWidget(self.prep_container)
        card_layout.addWidget(self.body_container)

        self.main_layout.addWidget(self.placeholder_widget, 1)
        self.main_layout.addWidget(self.card_container, 1)

    # ======================================================
    # Drag & Drop
    # ======================================================
    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat("application/x-magictable-tournament"):
            event.acceptProposedAction()

    def dropEvent(self, event):
        if self._current_tournament:
            event.ignore()
            return

        raw = event.mimeData().data("application/x-magictable-tournament")
        data = json.loads(bytes(raw).decode("utf-8"))

        tid = data.get("id")
        if tid is None:
            event.ignore()
            return

        upcoming_view = self._get_upcoming_view()
        if not upcoming_view:
            event.ignore()
            return

        tournament = upcoming_view.get_tournament_by_id(tid)
        if not tournament:
            event.ignore()
            return

        self._load_tournament(tournament)
        self.tournament_taken.emit(tournament.id)
        event.acceptProposedAction()

    # ======================================================
    # State
    # ======================================================
    def _load_tournament(self, tournament: Tournament):
        self._current_tournament = tournament

        self.placeholder_widget.hide()
        self.card_container.show()

        self.header_title.setText(tournament.name)
        self.header_format.setText(tournament.format)

        self._save_all()
        self._refresh_players_ui()

    def _edit_current_tournament(self):
        if self._current_tournament:
            self.edit_requested.emit(self._current_tournament)

    def _cancel_current_tournament(self):
        if not self._current_tournament:
            return

        tid = self._current_tournament.id
        self._clear_tournament()
        self.tournament_cancelled.emit(tid)

    def _clear_tournament(self):
        """Nettoie l'affichage du tournoi actuel (sans émettre de signal)."""
        self._current_tournament = None

        self.card_container.hide()
        self.placeholder_widget.show()

        self.players_list.clear()
        self.player_input.clear()
        self.tables_info.setText("🪑 0 joueur → 0 table")

    # ======================================================
    # Players
    # ======================================================
    def _add_player_manual(self):
        if not self._current_tournament:
            return

        name = self.player_input.text().strip()
        if not name:
            return

        player = self._current_tournament.add_player(name)
        if player is None:
            QMessageBox.warning(
                self,
                "Ajout impossible",
                "Nom invalide ou déjà utilisé."
            )
            return

        self.player_input.clear()
        self._save_all()
        self._refresh_players_ui()

    def _delete_selected_player(self):
        if not self._current_tournament:
            return

        item = self.players_list.currentItem()
        if not item:
            return

        player_id = item.data(Qt.UserRole)
        player_name = item.data(Qt.UserRole + 1) or item.text()

        reply = QMessageBox.question(
            self,
            "Supprimer le joueur",
            f"Supprimer définitivement « {player_name} » ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        self._current_tournament.remove_player(player_id)
        self._save_all()
        self._refresh_players_ui()

    def _browse_regular_players(self):
        """Ouvre le dialog de parcours des joueurs permanents."""
        if not self._current_tournament:
            return
        self._load_regular_players()
        dialog = BrowsePlayersDialog(self, self._regular_players, self._current_tournament)
        dialog.exec()
        self._save_all()
        self._refresh_players_ui()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete and self.players_list.hasFocus():
            self._delete_selected_player()
            event.accept()
            return

        super().keyPressEvent(event)

    def eventFilter(self, obj, event):
        """Intercepte Tab et Enter sur le popup ET le champ de saisie."""
        completer = self.player_input.completer()
        popup = completer.popup() if completer else None

        # ── Événements reçus par le POPUP (visible après frappe) ─────
        if popup is not None and obj is popup and event.type() == QEvent.KeyPress:
            key = event.key()

            if key == Qt.Key_Tab:
                # Initialiser la recherche au premier Tab sur ce popup
                if not self._completer_search_text:
                    self._completer_search_text = self.player_input.text()
                    self._completer_current_row = -1

                completer.setCompletionPrefix(self._completer_search_text)
                row_count = completer.completionCount()
                if row_count > 0:
                    # Avancer dans le cycle (% pour boucler)
                    self._completer_current_row = (self._completer_current_row + 1) % row_count
                    idx = completer.completionModel().index(self._completer_current_row, 0)
                    completion = completer.completionModel().data(idx)
                    if completion:
                        self.player_input.blockSignals(True)
                        self.player_input.setText(completion)
                        self.player_input.selectAll()
                        self.player_input.blockSignals(False)
                    # Restaurer le prefix puis ré-appliquer la sélection visuelle
                    completer.setCompletionPrefix(self._completer_search_text)
                    idx = completer.completionModel().index(self._completer_current_row, 0)
                    popup.setCurrentIndex(idx)
                return True  # Consommer Tab — ne pas déplacer le focus

            if key in (Qt.Key_Return, Qt.Key_Enter):
                cur = popup.currentIndex()
                if cur.isValid():
                    completion = completer.completionModel().data(cur)
                    if completion:
                        self.player_input.setText(completion)
                self._completer_search_text = ""
                self._completer_current_row = -1
                popup.hide()
                self._add_player_manual()
                return True

        # ── Événements reçus par le CHAMP de saisie ──────────────────
        if obj is self.player_input:
            if event.type() == QEvent.FocusIn:
                self._load_regular_players()
                self._setup_completer()
            elif event.type() == QEvent.FocusOut:
                self._completer_search_text = ""
                self._completer_current_row = -1
            elif event.type() == QEvent.KeyPress and event.key() == Qt.Key_Tab:
                # Popup pas encore ouvert : l'ouvrir et sélectionner le 1er résultat
                if self.player_input.text().strip() and completer:
                    self._completer_search_text = self.player_input.text()
                    self._completer_current_row = 0
                    completer.setCompletionPrefix(self._completer_search_text)
                    if completer.completionCount() > 0:
                        completer.complete()
                        idx = completer.completionModel().index(0, 0)
                        completer.popup().setCurrentIndex(idx)
                        completion = completer.completionModel().data(idx)
                        if completion:
                            self.player_input.blockSignals(True)
                            self.player_input.setText(completion)
                            self.player_input.selectAll()
                            self.player_input.blockSignals(False)
                        completer.setCompletionPrefix(self._completer_search_text)
                        idx = completer.completionModel().index(0, 0)
                        completer.popup().setCurrentIndex(idx)
                return True  # Consommer Tab dans tous les cas

        return super().eventFilter(obj, event)

    def _on_player_double_clicked(self, item: QListWidgetItem):
        """Double-clic sur un joueur : ouvre le dialogue commandant si format Commander."""
        if not self._current_tournament or not self._is_commander_format():
            return

        player_id = item.data(Qt.UserRole)
        if player_id is not None:
            self._edit_commander(player_id)

    def _show_player_context_menu(self, pos):
        if not self._current_tournament:
            return

        item = self.players_list.itemAt(pos)
        if not item:
            return

        # Récupérer le nom original du joueur
        player_name = item.data(Qt.UserRole + 1) or item.text()
        player_id = item.data(Qt.UserRole)
        is_regular = self._is_regular_player(player_name)

        menu = QMenu(self)

        # Option commandant (formats Commander uniquement)
        commander_action = None
        if self._is_commander_format():
            player = next(
                (p for p in self._current_tournament.players if p.id == player_id),
                None,
            )
            if player and player.commander:
                commander_action = menu.addAction(f"🛡️ {player.commander}")
            else:
                commander_action = menu.addAction("🛡️ Ajouter un commandant")
            menu.addSeparator()

        # Option joueur permanent
        if is_regular:
            regular_action = menu.addAction("⭐ Joueur permanent")
            regular_action.setEnabled(False)
        else:
            add_regular_action = menu.addAction("➕ Ajouter aux joueurs permanents")

        menu.addSeparator()
        edit_action = menu.addAction("✏️ Modifier")
        menu.addSeparator()
        delete_action = menu.addAction("🗑️ Supprimer")

        action = menu.exec(self.players_list.mapToGlobal(pos))

        if action is None:
            return

        if action == commander_action:
            self._edit_commander(player_id)
        elif action == edit_action:
            self._edit_player(item)
        elif action == delete_action:
            self.players_list.setCurrentItem(item)
            self._delete_selected_player()
        elif not is_regular and action.text().startswith("➕"):
            self._add_to_regular_players(player_name)

    def _add_to_regular_players(self, name: str):
        """Ajoute un joueur à la liste des joueurs permanents."""
        # Charger les joueurs existants
        raw = RegularPlayerStorage.load()
        regular_players = [RegularPlayer.from_dict(d) for d in raw]

        # Vérifier si le joueur existe déjà
        name_lower = name.lower().strip()
        if any(p.pseudo.lower().strip() == name_lower for p in regular_players):
            QMessageBox.information(
                self,
                "Joueur existant",
                f"« {name} » est déjà dans la liste des joueurs permanents."
            )
            return

        # Créer le nouveau joueur
        next_id = max((p.id for p in regular_players), default=0) + 1
        new_player = RegularPlayer(
            id=next_id,
            pseudo=name,
        )

        regular_players.append(new_player)

        # Sauvegarder
        RegularPlayerStorage.save([p.to_dict() for p in regular_players])

        # Rafraîchir l'affichage pour montrer l'étoile
        self._refresh_players_ui()

        QMessageBox.information(
            self,
            "Joueur ajouté",
            f"« {name} » a été ajouté aux joueurs permanents."
        )

    def _edit_player(self, item: QListWidgetItem):
        if not self._current_tournament:
            return

        player_id = item.data(Qt.UserRole)
        # Utiliser le nom original (sans la pastille)
        old_name = item.data(Qt.UserRole + 1) or item.text()

        dialog = EditPlayerDialog(self, name=old_name)
        if dialog.exec() != 1:
            return

        new_name = dialog.value()
        if not new_name:
            return

        if not self._current_tournament.rename_player(player_id, new_name):
            QMessageBox.warning(
                self,
                "Nom invalide",
                "Impossible de renommer le joueur."
            )
            return

        self._save_all()
        self._refresh_players_ui()

    def _edit_commander(self, player_id: int):
        """Ouvre un dialogue pour définir/modifier le commandant d'un joueur."""
        if not self._current_tournament:
            return

        player = next(
            (p for p in self._current_tournament.players if p.id == player_id),
            None,
        )
        if not player:
            return

        text, ok = QInputDialog.getText(
            self,
            "Commandant",
            f"Commandant de {player.name} :",
            QLineEdit.Normal,
            player.commander,
        )

        if not ok:
            return

        player.commander = text.strip()
        self._save_all()
        self._refresh_players_ui()

    # ======================================================
    # UI Refresh
    # ======================================================
    def _update_tables_info(self):
        if not self._current_tournament:
            self.tables_info.setText("🪑 0 joueur → 0 table")
            self.reco_rounds_label.setText("")
            return

        tournament = self._current_tournament
        players = tournament.player_count
        table_count = tournament.table_count() or 0

        self.tables_info.setText(
            f"🪑 {players} joueur{'s' if players > 1 else ''} → "
            f"{table_count} table{'s' if table_count > 1 else ''}"
        )

        if players >= 2:
            reco = compute_recommended_rounds(players)
            self.reco_rounds_label.setText(f"💡 Rounds recommandés : {reco}")
        else:
            self.reco_rounds_label.setText("")

    def _refresh_meta(self):
        if not self._current_tournament:
            self.header_meta.setText("")
            return

        t = self._current_tournament
        self.header_meta.setText(f"{t.date} • {t.player_count} joueurs")

    def _is_regular_player(self, name: str) -> bool:
        """Vérifie si le nom correspond à un joueur régulier."""
        # Rafraîchir la liste pour avoir les derniers joueurs ajoutés
        self._load_regular_players()
        name_lower = name.lower().strip()
        return any(p.pseudo.lower().strip() == name_lower for p in self._regular_players)

    def _is_commander_format(self) -> bool:
        """Vérifie si le tournoi utilise un format Commander."""
        if not self._current_tournament:
            return False
        return "Commander" in self._current_tournament.format

    def _refresh_players_ui(self):
        if not self._current_tournament:
            return

        # Rafraîchir la liste des joueurs réguliers
        self._load_regular_players()
        self._setup_completer()

        # Créer un set des pseudos réguliers pour une recherche rapide
        regular_pseudos = {p.pseudo.lower().strip() for p in self._regular_players}

        is_commander = self._is_commander_format()

        self.players_list.clear()
        for player in self._current_tournament.players:
            # Ajouter une pastille si c'est un joueur régulier
            player_name_lower = player.name.lower().strip()
            if player_name_lower in regular_pseudos:
                display_name = f"⭐ {player.name}"
            else:
                display_name = player.name

            # Format Commander : afficher le commandant ou ⚠️ si absent
            if is_commander:
                if player.commander:
                    display_name = f"{display_name}  |  {player.commander}"
                else:
                    display_name = f"⚠️ {display_name}"

            item = QListWidgetItem(display_name)
            item.setData(Qt.UserRole, player.id)
            # Stocker le nom original pour l'édition
            item.setData(Qt.UserRole + 1, player.name)
            self.players_list.addItem(item)

        self._refresh_meta()
        self._update_tables_info()

        # Commander : min 6 joueurs (tables de 3-4), autres formats : min 4 (tables de 2)
        if self._current_tournament.format == "👑 Commander":
            min_players = 6
            can_start = self._current_tournament.player_count >= min_players
        else:
            min_players = 4
            can_start = self._current_tournament.player_count >= min_players

        # Afficher ou cacher le message de minimum joueurs
        if self._current_tournament.player_count < min_players:
            self.min_players_label.setText(f"Minimum {min_players} joueurs requis")
            self.min_players_label.show()
        else:
            self.min_players_label.hide()

        # Duel Commander : tous les commandants requis
        if self._current_tournament.format == "⚔️ Duel Commander":
            all_have_commander = all(
                p.commander for p in self._current_tournament.players
            )
            if self._current_tournament.players and not all_have_commander:
                can_start = False
                self.commander_warning.setText(
                    "⚠️ Tous les commandants doivent être renseignés"
                )
                self.commander_warning.show()
            else:
                self.commander_warning.hide()
        else:
            self.commander_warning.hide()

        self.start_btn.setEnabled(can_start)

    def _start_tournament(self):
        if not self._current_tournament:
            return

        t = self._current_tournament
        if t.is_1v1_format():
            reco = compute_recommended_rounds(t.player_count)
            if t.max_rounds != reco:
                reply = QMessageBox.warning(
                    self,
                    "Nombre de rounds inhabituel",
                    f"Le nombre de rounds configuré ({t.max_rounds}) est différent "
                    f"du recommandé pour {t.player_count} joueurs ({reco} rounds).\n\n"
                    f"Voulez-vous quand même lancer le tournoi ?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No,
                )
                if reply != QMessageBox.Yes:
                    return

        self.start_requested.emit(t)

    def _save_all(self):
        upcoming_view = self._get_upcoming_view()
        if not upcoming_view:
            return

        TournamentStorage.save(
            [t.to_dict() for t in upcoming_view._tournaments]
        )
