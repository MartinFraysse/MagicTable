from PySide6.QtCore import Qt, QRect, QModelIndex
from PySide6.QtGui import QPalette, QColor, QPainter, QBrush, QShortcut, QKeySequence
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

from core.regular_player import RegularPlayer
from core.tournament import Tournament
from core.stats_analyzer import StatsAnalyzer
from storage.regular_players import RegularPlayerStorage
from storage.tournaments import TournamentStorage
from ui.players.dialogs.create_player import CreatePlayerDialog


class RowBackgroundDelegate(QStyledItemDelegate):
    """Delegate pour dessiner un fond unifié sur toute la ligne."""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Couleurs opaques (fond #0f241d + teinte verte)
        self._hover_color = QColor(20, 53, 38)      # Hover subtil
        self._selected_color = QColor(24, 70, 48)   # Sélection visible

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        table = option.widget
        if table is None:
            super().paint(painter, option, index)
            return

        col = index.column()
        row = index.row()
        col_count = table.columnCount()

        # Vérifier si la ligne est sélectionnée
        is_selected = table.selectionModel().isRowSelected(row, index.parent())

        # Vérifier si la ligne est survolée (pas juste la cellule)
        cursor_pos = table.viewport().mapFromGlobal(table.cursor().pos())
        hovered_index = table.indexAt(cursor_pos)
        is_hovered = hovered_index.isValid() and hovered_index.row() == row and not is_selected

        # Dessiner le fond de cette cellule seulement
        if is_selected or is_hovered:
            painter.save()
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.NoPen)

            if is_selected:
                painter.setBrush(QBrush(self._selected_color))
            else:
                painter.setBrush(QBrush(self._hover_color))

            # Calculer le rectangle de cette cellule avec marges
            cell_rect = option.rect.adjusted(0, 2, 0, -2)

            # Ajuster pour première/dernière colonne (marges + coins arrondis)
            if col == 0:
                cell_rect.setLeft(cell_rect.left() + 4)
            if col == col_count - 1:
                cell_rect.setRight(cell_rect.right() - 4)

            # Dessiner avec coins arrondis appropriés via clipping
            if col == 0 and col == col_count - 1:
                # Une seule colonne : tous les coins arrondis
                painter.drawRoundedRect(cell_rect, 6, 6)
            elif col == 0:
                # Première colonne : coins arrondis à gauche
                painter.setClipRect(cell_rect)
                extended = cell_rect.adjusted(0, 0, 10, 0)
                painter.drawRoundedRect(extended, 6, 6)
            elif col == col_count - 1:
                # Dernière colonne : coins arrondis à droite
                painter.setClipRect(cell_rect)
                extended = cell_rect.adjusted(-10, 0, 0, 0)
                painter.drawRoundedRect(extended, 6, 6)
            else:
                # Colonnes du milieu : rectangle simple
                painter.drawRect(cell_rect)

            painter.restore()

        # Retirer les états hover/selected pour éviter le fond par défaut
        opt = QStyleOptionViewItem(option)
        opt.state &= ~QStyle.State_Selected
        opt.state &= ~QStyle.State_MouseOver

        # Dessiner le contenu sans le fond de sélection par défaut
        super().paint(painter, opt, index)


class PlayersViewMain(QWidget):
    """Vue principale de la section Joueurs."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("PlayersViewMain")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._players: list[RegularPlayer] = []
        self._next_id = 1
        self._calculated_points: dict[str, int] = {}  # pseudo.lower() -> points calculés
        self._analyzer: StatsAnalyzer | None = None
        self._search_text: str = ""

        self._build_ui()
        self._load_players()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header
        header = self._build_header()
        layout.addWidget(header)

        # Table des joueurs
        self.table = self._build_table()
        layout.addWidget(self.table, 1)

    def _build_header(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("PlayersHeader")

        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("👥 Joueurs réguliers")
        title.setObjectName("SectionTitle")

        self.count_label = QLabel("")
        self.count_label.setObjectName("CountLabel")

        self.search_input = QLineEdit()
        self.search_input.setObjectName("PlayersSearchInput")
        self.search_input.setPlaceholderText("🔍 Rechercher un joueur…")
        self.search_input.setFixedWidth(240)
        self.search_input.setClearButtonEnabled(True)
        self.search_input.textChanged.connect(self._on_search_changed)

        add_btn = QPushButton("➕ Ajouter un joueur")
        add_btn.setObjectName("PrimaryButton")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._add_player)

        layout.addWidget(title)
        layout.addWidget(self.count_label)
        layout.addStretch()
        layout.addWidget(self.search_input)
        layout.addWidget(add_btn)

        return frame

    def _build_table(self) -> QTableWidget:
        table = QTableWidget()
        table.setObjectName("PlayersTable")

        # Colonnes
        columns = ["Pseudo", "Nom complet", "Téléphone", "Discord", "Points", "🥇", "🥈", "🥉", "Podiums"]
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)

        # Style
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setAlternatingRowColors(False)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setFrameShape(QFrame.NoFrame)

        # Hauteur des lignes
        table.verticalHeader().setDefaultSectionSize(44)

        # Éviter les coins blancs et la sélection bleue
        palette = table.palette()
        palette.setColor(QPalette.Base, QColor("#0f241d"))
        palette.setColor(QPalette.Highlight, QColor("#0f241d"))  # Même couleur que le fond
        palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
        table.setPalette(palette)
        table.viewport().setAutoFillBackground(True)

        # Delegate pour fond de ligne unifié
        delegate = RowBackgroundDelegate(table)
        table.setItemDelegate(delegate)

        # Activer le mouse tracking pour le hover
        table.setMouseTracking(True)
        table.viewport().setMouseTracking(True)

        # Largeurs des colonnes
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)          # Pseudo
        header.setSectionResizeMode(1, QHeaderView.Stretch)          # Nom complet
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents) # Téléphone
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents) # Discord
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents) # Points
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents) # Top 1
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents) # Top 2
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents) # Top 3
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents) # Podiums

        # Menu contextuel
        table.setContextMenuPolicy(Qt.CustomContextMenu)
        table.customContextMenuRequested.connect(self._show_context_menu)

        # Double-clic pour éditer
        table.doubleClicked.connect(self._edit_selected_player)

        # Touche Suppr pour supprimer
        delete_shortcut = QShortcut(QKeySequence(Qt.Key_Delete), table)
        delete_shortcut.activated.connect(self._delete_selected_player)

        return table

    def _load_players(self):
        """Charge les joueurs depuis le storage."""
        raw = RegularPlayerStorage.load()
        self._players = [RegularPlayer.from_dict(d) for d in raw]

        if self._players:
            self._next_id = max(p.id for p in self._players) + 1

        # Calculer les points depuis les tournois archivés
        self._calculate_points_from_tournaments()

        self._refresh_table()

    def _calculate_points_from_tournaments(self):
        """Calcule les points de chaque joueur depuis les tournois archivés."""
        raw_tournaments = TournamentStorage.load()
        tournaments = [Tournament.from_dict(t) for t in raw_tournaments]

        self._analyzer = StatsAnalyzer(tournaments)
        top_players = self._analyzer.get_top_players(limit=1000)

        self._calculated_points = {
            p.name.lower().strip(): p.total_points
            for p in top_players
        }

    def _save_players(self):
        """Sauvegarde les joueurs dans le storage."""
        RegularPlayerStorage.save([p.to_dict() for p in self._players])

    def _get_player_points(self, player: RegularPlayer) -> int:
        """Retourne les points calculés pour un joueur."""
        return self._calculated_points.get(player.pseudo.lower().strip(), 0)

    def _on_search_changed(self, text: str):
        self._search_text = text.strip().lower()
        self._refresh_table()

    def _refresh_table(self):
        """Rafraîchit la table des joueurs."""
        # Trier par points calculés décroissants, puis par pseudo
        self._players.sort(key=lambda p: (-self._get_player_points(p), p.pseudo.lower()))

        # Filtrer selon la recherche
        filtered = self._players
        if self._search_text:
            filtered = [
                p for p in self._players
                if self._search_text in p.pseudo.lower()
                or self._search_text in p.full_name.lower()
            ]

        self.table.setRowCount(len(filtered))

        for row, player in enumerate(filtered):
            self._set_row(row, player)

        # Mise à jour du compteur
        total = len(self._players)
        shown = len(filtered)
        if self._search_text and shown < total:
            self.count_label.setText(f"({shown}/{total})")
        else:
            self.count_label.setText(f"({total})" if total > 0 else "")

    def refresh(self):
        """Recharge les joueurs depuis le storage et rafraîchit la table."""
        self._load_players()

    def _format_phone(self, phone: str) -> str:
        """Formate le numéro de téléphone en xx xx xx xx xx."""
        # Retirer tous les caractères non numériques
        digits = ''.join(c for c in phone if c.isdigit())

        # Si on a 10 chiffres, formater
        if len(digits) == 10:
            return ' '.join(digits[i:i+2] for i in range(0, 10, 2))

        # Sinon retourner tel quel
        return phone

    def _set_row(self, row: int, player: RegularPlayer):
        """Remplit une ligne de la table."""
        # Utiliser les points calculés depuis les tournois
        calculated_points = self._get_player_points(player)

        if player.discord_id:
            discord_label = player.discord_pseudo if player.discord_pseudo else "🔗 Lié"
        else:
            discord_label = "—"
        items = [
            (player.pseudo, player.id),
            (player.full_name, None),
            (self._format_phone(player.phone), None),
            (discord_label, None),
            (str(calculated_points), None),
            (str(player.top_1), None),
            (str(player.top_2), None),
            (str(player.top_3), None),
            (str(player.total_podiums), None),
        ]

        for col, (text, data) in enumerate(items):
            item = QTableWidgetItem(text)
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)

            if data is not None:
                item.setData(Qt.UserRole, data)

            item.setTextAlignment(Qt.AlignCenter)

            self.table.setItem(row, col, item)

    def _get_existing_pseudos(self) -> list[str]:
        """Retourne la liste des pseudos existants."""
        return [p.pseudo for p in self._players]

    def _add_player(self):
        """Ouvre le dialog pour ajouter un joueur."""
        dialog = CreatePlayerDialog(
            self,
            existing_pseudos=self._get_existing_pseudos(),
        )

        if not dialog.exec():
            return

        data = dialog.get_data()

        player = RegularPlayer(
            id=self._next_id,
            pseudo=data["pseudo"],
            full_name=data["full_name"],
            phone=data["phone"],
            discord_id=data["discord_id"],
        )

        self._next_id += 1
        self._players.append(player)

        self._save_players()
        self._refresh_table()

    def _edit_selected_player(self):
        """Édite le joueur sélectionné."""
        row = self.table.currentRow()
        if row < 0:
            return

        item = self.table.item(row, 0)
        if not item:
            return

        player_id = item.data(Qt.UserRole)
        player = next((p for p in self._players if p.id == player_id), None)

        if not player:
            return

        dialog = CreatePlayerDialog(
            self,
            player=player,
            existing_pseudos=self._get_existing_pseudos(),
        )

        if not dialog.exec():
            return

        dialog.apply_changes()

        self._save_players()
        self._refresh_table()

    def _delete_selected_player(self):
        """Supprime le joueur sélectionné."""
        row = self.table.currentRow()
        if row < 0:
            return

        item = self.table.item(row, 0)
        if not item:
            return

        player_id = item.data(Qt.UserRole)
        player = next((p for p in self._players if p.id == player_id), None)

        if not player:
            return

        reply = QMessageBox.question(
            self,
            "Supprimer le joueur",
            f"Supprimer définitivement « {player.pseudo} » ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if reply != QMessageBox.Yes:
            return

        self._players = [p for p in self._players if p.id != player_id]

        self._save_players()
        self._refresh_table()

    def _show_context_menu(self, pos):
        """Affiche le menu contextuel."""
        item = self.table.itemAt(pos)
        if not item:
            return

        row = self.table.currentRow()
        player = self._get_selected_player()

        menu = QMenu(self)

        stats_action = menu.addAction("📊 Statistiques")
        menu.addSeparator()
        edit_action = menu.addAction("✏️ Modifier")

        unlink_action = None
        if player and player.discord_id:
            menu.addSeparator()
            label = f"🔓 Délier Discord ({player.discord_pseudo})" if player.discord_pseudo else "🔓 Délier Discord"
            unlink_action = menu.addAction(label)

        menu.addSeparator()
        delete_action = menu.addAction("🗑️ Supprimer")

        action = menu.exec(self.table.viewport().mapToGlobal(pos))

        if action == stats_action:
            self._show_player_stats()
        elif action == edit_action:
            self._edit_selected_player()
        elif unlink_action and action == unlink_action:
            self._unlink_discord(player)
        elif action == delete_action:
            self._delete_selected_player()

    def _get_selected_player(self) -> "RegularPlayer | None":
        """Retourne le joueur correspondant à la ligne sélectionnée."""
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        if not item:
            return None
        player_id = item.data(Qt.UserRole)
        return next((p for p in self._players if p.id == player_id), None)

    def _unlink_discord(self, player: "RegularPlayer"):
        """Délie le compte Discord du joueur."""
        name = player.discord_pseudo or player.discord_id
        reply = QMessageBox.question(
            self,
            "Délier Discord",
            f"Délier le compte Discord « {name} » du joueur « {player.pseudo} » ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        player.discord_id = ""
        player.discord_pseudo = ""
        self._save_players()
        self._refresh_table()

    def _show_player_stats(self):
        """Affiche les statistiques du joueur sélectionné."""
        row = self.table.currentRow()
        if row < 0:
            return

        item = self.table.item(row, 0)
        if not item:
            return

        player_id = item.data(Qt.UserRole)
        player = next((p for p in self._players if p.id == player_id), None)

        if not player:
            return

        from ui.players.dialogs.player_stats import PlayerStatsDialog
        dialog = PlayerStatsDialog(self, player, self._analyzer)
        dialog.exec()
