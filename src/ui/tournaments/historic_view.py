from PySide6.QtCore import Qt, Signal, QTimer, QEvent
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QFrame,
    QLabel,
    QDialog,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QMenu,
    QMessageBox,
    QCheckBox,
    QFileDialog,
)

from core.tournament import Tournament
from core.regular_player import RegularPlayer
from storage.regular_players import RegularPlayerStorage
from export.pdf_export import export_tournament_pdf


class HistoricView(QWidget):
    """
    Vue d'accès à l'historique des tournois archivés.
    """

    tournament_deleted = Signal(int)  # Émet l'ID du tournoi supprimé
    tournaments_changed = Signal()  # Émet quand les données sont modifiées

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("HistoricView")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._archived_tournaments: list[Tournament] = []

        self._build_ui()

    # =========================
    # UI
    # =========================
    def _build_ui(self):
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        container = QFrame()
        container.setObjectName("HistoricContainerInner")
        container.setAttribute(Qt.WA_StyledBackground, True)

        layout = QHBoxLayout(container)
        layout.setContentsMargins(12, 8, 12, 8)

        layout.addStretch()

        self.history_btn = QPushButton("📜 Historique des tournois")
        self.history_btn.setObjectName("HistoricPrimaryButton")
        self.history_btn.setCursor(Qt.PointingHandCursor)
        self.history_btn.clicked.connect(self._show_history_dialog)

        self.count_label = QLabel("")
        self.count_label.setObjectName("HistoricCountLabel")

        layout.addWidget(self.history_btn)
        layout.addWidget(self.count_label)

        root_layout.addWidget(container, 1)

    # =========================
    # Public API
    # =========================
    def refresh_archived_tournaments(self, all_tournaments: list[Tournament]):
        """Met à jour la liste des tournois archivés."""
        self._archived_tournaments = [t for t in all_tournaments if t.archived]
        count = len(self._archived_tournaments)
        if count > 0:
            self.count_label.setText(f"({count})")
        else:
            self.count_label.setText("")

    # =========================
    # Dialog
    # =========================
    def _show_history_dialog(self):
        if not self._archived_tournaments:
            return

        dialog = HistoricDialog(self, self._archived_tournaments)
        dialog.tournament_deleted.connect(self._on_tournament_deleted)
        dialog.tournaments_changed.connect(self._on_tournaments_changed)
        dialog.exec()

    def _on_tournaments_changed(self):
        """Appelé quand les données d'un tournoi sont modifiées."""
        self.tournaments_changed.emit()

    def _on_tournament_deleted(self, tournament_id: int):
        """Appelé quand un tournoi est supprimé depuis le dialog."""
        self._archived_tournaments = [
            t for t in self._archived_tournaments if t.id != tournament_id
        ]
        count = len(self._archived_tournaments)
        if count > 0:
            self.count_label.setText(f"({count})")
        else:
            self.count_label.setText("")
        self.tournament_deleted.emit(tournament_id)


class HistoricDialog(QDialog):
    """Dialog affichant la liste des tournois archivés."""

    tournament_deleted = Signal(int)  # Émet l'ID du tournoi supprimé
    tournaments_changed = Signal()  # Émet quand les données sont modifiées

    def __init__(self, parent, tournaments: list[Tournament]):
        super().__init__(parent)

        self.setWindowTitle("Historique des tournois")
        self.setModal(True)
        self.setMinimumSize(600, 500)
        self.setObjectName("HistoricDialog")

        self._tournaments = tournaments
        self._tournaments_by_id = {t.id: t for t in tournaments}
        self._cards_by_id: dict[int, QFrame] = {}

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("📜 Tournois archivés")
        title.setObjectName("DialogTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Liste des tournois
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(12)

        for tournament in self._tournaments:
            card = self._create_tournament_card(tournament)
            self._cards_by_id[tournament.id] = card
            content_layout.addWidget(card)

        self._content_layout = content_layout

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Bouton fermer
        close_btn = QPushButton("Fermer")
        close_btn.setObjectName("CancelButton")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)

    def eventFilter(self, obj, event):
        """Double-clic sur une carte ouvre les détails."""
        if event.type() == QEvent.MouseButtonDblClick and isinstance(obj, QFrame):
            tid = obj.property("tournament_id")
            if tid is not None:
                self._show_detail_dialog(tid)
                return True
        return super().eventFilter(obj, event)

    def _create_tournament_card(self, tournament: Tournament) -> QFrame:
        card = QFrame()
        card.setObjectName("HistoricCard")
        card.setProperty("tournament_id", tournament.id)
        card.setProperty("tournament_name", tournament.name)
        card.setContextMenuPolicy(Qt.CustomContextMenu)
        card.customContextMenuRequested.connect(
            lambda pos, c=card: self._show_context_menu(pos, c)
        )
        card.installEventFilter(self)

        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        # Header
        header = QHBoxLayout()
        name_label = QLabel(f"<b>{tournament.name}</b>")
        name_label.setObjectName("HistoricCardTitle")

        format_label = QLabel(tournament.format)
        format_label.setObjectName("HistoricCardFormat")

        date_label = QLabel(tournament.date)
        date_label.setObjectName("HistoricCardDate")

        header.addWidget(name_label)
        header.addWidget(format_label)
        header.addStretch()
        header.addWidget(date_label)

        layout.addLayout(header)

        # Classement (top 3)
        players = sorted(tournament.players, key=lambda p: (-p.score, p.name))

        ranking_layout = QHBoxLayout()
        for rank, player in enumerate(players[:3], 1):
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, "")
            label = QLabel(f"{medal} {player.name} ({player.score} pts)")
            label.setObjectName("HistoricCardRanking")
            ranking_layout.addWidget(label)

        ranking_layout.addStretch()
        layout.addLayout(ranking_layout)

        # Stats
        stats = QLabel(f"{len(tournament.players)} joueurs • {len(tournament.rounds)} rounds")
        stats.setObjectName("HistoricCardStats")
        layout.addWidget(stats)

        return card

    def _show_context_menu(self, pos, card: QFrame):
        """Affiche le menu contextuel pour une carte de tournoi."""
        tournament_id = card.property("tournament_id")
        tournament_name = card.property("tournament_name")

        menu = QMenu(self)
        detail_action = menu.addAction("📋 Détails")
        menu.addSeparator()
        rewards_action = menu.addAction("🎁 Récompenses")
        export_action = menu.addAction("📄 Exporter PDF")
        menu.addSeparator()
        delete_action = menu.addAction("🗑️ Supprimer définitivement")

        action = menu.exec(card.mapToGlobal(pos))

        if action == detail_action:
            self._show_detail_dialog(tournament_id)
        elif action == rewards_action:
            self._show_rewards_dialog(tournament_id)
        elif action == export_action:
            self._export_tournament_pdf(tournament_id, tournament_name)
        elif action == delete_action:
            self._delete_tournament(tournament_id, tournament_name)

    def _show_detail_dialog(self, tournament_id: int):
        """Affiche les détails complets d'un tournoi."""
        tournament = self._tournaments_by_id.get(tournament_id)
        if not tournament:
            return
        dialog = TournamentDetailDialog(self, tournament)
        dialog.exec()

    def _show_rewards_dialog(self, tournament_id: int):
        """Affiche le dialogue des récompenses pour un tournoi."""
        tournament = self._tournaments_by_id.get(tournament_id)
        if not tournament:
            return

        dialog = RewardsDialog(self, tournament)
        if dialog.exec():
            self.tournaments_changed.emit()

    def _export_tournament_pdf(self, tournament_id: int, tournament_name: str):
        """Exporte un tournoi en PDF."""
        tournament = self._tournaments_by_id.get(tournament_id)
        if not tournament:
            return

        # Nom de fichier par défaut basé sur le nom du tournoi
        safe_name = "".join(c for c in tournament_name if c.isalnum() or c in " -_").strip()
        default_filename = f"{safe_name}.pdf"

        # Utiliser le dialog Qt (non-natif) pour appliquer les styles
        dialog = QFileDialog(self, "Exporter en PDF")
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setNameFilter("Fichiers PDF (*.pdf)")
        dialog.setDefaultSuffix("pdf")
        dialog.selectFile(default_filename)
        dialog.setOption(QFileDialog.DontUseNativeDialog, True)
        dialog.setMinimumSize(700, 500)

        # Fixer les labels pour éviter le changement Open/Save
        dialog.setLabelText(QFileDialog.Accept, "Enregistrer")
        dialog.setLabelText(QFileDialog.Reject, "Annuler")
        dialog.setLabelText(QFileDialog.FileName, "Nom du fichier :")
        dialog.setLabelText(QFileDialog.LookIn, "Emplacement :")
        dialog.setLabelText(QFileDialog.FileType, "Type :")

        # Ajouter un bouton "Ouvrir" séparé pour naviguer dans les dossiers
        from PySide6.QtWidgets import QDialogButtonBox, QPushButton, QTreeView, QListView
        button_box = dialog.findChild(QDialogButtonBox)

        # Créer le bouton "Ouvrir dossier"
        open_folder_btn = QPushButton("Ouvrir")
        open_folder_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #2f4f46, stop:1 #1f352f);
                color: #d3e6df;
                border: 1px solid #5fa693;
                min-height: 32px;
                min-width: 90px;
                padding: 6px 14px;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #3b6b5f, stop:1 #26443d);
                border-color: #7fd9bb;
            }
            QPushButton:pressed {
                background: #1a2f29;
            }
            QPushButton:disabled {
                background: #1a2f29;
                color: #6f8f84;
                border-color: #3f5f55;
            }
        """)

        # Trouver les vues pour la navigation
        tree_view = dialog.findChild(QTreeView)
        list_view = dialog.findChild(QListView)

        def open_selected_folder():
            """Ouvre le dossier sélectionné."""
            indexes = []
            if tree_view and tree_view.isVisible():
                indexes = tree_view.selectedIndexes()
            elif list_view and list_view.isVisible():
                indexes = list_view.selectedIndexes()

            if indexes:
                index = indexes[0]
                model = index.model()
                if model and model.isDir(index):
                    path = model.filePath(index)
                    dialog.setDirectory(path)

        def update_open_button():
            """Active/désactive le bouton Ouvrir selon la sélection."""
            indexes = []
            if tree_view and tree_view.isVisible():
                indexes = tree_view.selectedIndexes()
            elif list_view and list_view.isVisible():
                indexes = list_view.selectedIndexes()

            is_dir = False
            if indexes:
                index = indexes[0]
                model = index.model()
                if model:
                    is_dir = model.isDir(index)

            open_folder_btn.setEnabled(is_dir)

        open_folder_btn.clicked.connect(open_selected_folder)
        open_folder_btn.setEnabled(False)

        # Connecter les signaux de sélection
        if tree_view:
            tree_view.selectionModel().selectionChanged.connect(lambda: update_open_button())
        if list_view:
            list_view.selectionModel().selectionChanged.connect(lambda: update_open_button())

        if button_box:
            # Insérer le bouton Ouvrir avant Enregistrer
            button_box.addButton(open_folder_btn, QDialogButtonBox.ActionRole)

            # Bouton Enregistrer - style primaire vert
            save_btn = button_box.button(QDialogButtonBox.Save)
            if save_btn:
                save_btn.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #34cfa1, stop:1 #1f7a5a);
                        color: #eafff7;
                        border: 1px solid #55e0b6;
                        font-weight: 700;
                        min-height: 32px;
                        min-width: 100px;
                        padding: 6px 18px;
                        border-radius: 8px;
                        font-size: 13px;
                    }
                    QPushButton:hover {
                        background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #55e0b6, stop:1 #2fb38a);
                    }
                    QPushButton:pressed {
                        background: #17664a;
                    }
                """)

            # Bouton Annuler - style secondaire
            cancel_btn = button_box.button(QDialogButtonBox.Cancel)
            if cancel_btn:
                cancel_btn.setStyleSheet("""
                    QPushButton {
                        background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #2f4f46, stop:1 #1f352f);
                        color: #d3e6df;
                        border: 1px solid #5fa693;
                        min-height: 32px;
                        min-width: 100px;
                        padding: 6px 18px;
                        border-radius: 8px;
                        font-size: 13px;
                        font-weight: 600;
                    }
                    QPushButton:hover {
                        background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 #3b6b5f, stop:1 #26443d);
                        border-color: #7fd9bb;
                    }
                    QPushButton:pressed {
                        background: #1a2f29;
                    }
                """)

        if not dialog.exec():
            return

        files = dialog.selectedFiles()
        if not files:
            return

        filepath = files[0]

        if export_tournament_pdf(tournament, filepath):
            QMessageBox.information(
                self,
                "Export réussi",
                f"Le tournoi a été exporté vers :\n{filepath}"
            )
        else:
            QMessageBox.warning(
                self,
                "Erreur d'export",
                "Une erreur est survenue lors de l'export PDF."
            )

    def _delete_tournament(self, tournament_id: int, tournament_name: str):
        """Supprime un tournoi archivé après confirmation."""
        reply = QMessageBox.question(
            self,
            "Supprimer le tournoi",
            f"Supprimer définitivement « {tournament_name} » de l'historique ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # Stocker l'ID à supprimer et fermer le dialog
        self._pending_delete_id = tournament_id
        self.accept()

    def accept(self):
        """Ferme le dialog et émet le signal si suppression en attente."""
        pending_id = getattr(self, '_pending_delete_id', None)
        super().accept()
        if pending_id is not None:
            self.tournament_deleted.emit(pending_id)


class RewardsDialog(QDialog):
    """Dialog pour gérer les récompenses des joueurs d'un tournoi."""

    def __init__(self, parent, tournament: Tournament):
        super().__init__(parent)

        self.setWindowTitle(f"Récompenses — {tournament.name}")
        self.setModal(True)
        self.setMinimumSize(400, 450)
        self.setObjectName("RewardsDialog")

        self._tournament = tournament
        self._checkboxes: dict[int, QCheckBox] = {}
        self._regular_pseudos: set[str] = self._load_regular_pseudos()

        self._build_ui()

    def _load_regular_pseudos(self) -> set[str]:
        """Charge les pseudos des joueurs réguliers."""
        raw = RegularPlayerStorage.load()
        players = [RegularPlayer.from_dict(d) for d in raw]
        return {p.pseudo.lower().strip() for p in players}

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("🎁 Récompenses récupérées")
        title.setObjectName("DialogTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        subtitle = QLabel("Cochez les joueurs ayant récupéré leur récompense")
        subtitle.setObjectName("DialogSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)

        # Liste des joueurs avec checkboxes
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(8)

        # Trier les joueurs par score (classement)
        players = sorted(
            self._tournament.players,
            key=lambda p: (-p.score, p.name)
        )

        for rank, player in enumerate(players, 1):
            row = QFrame()
            row.setObjectName("RewardRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(8, 4, 8, 4)

            # Médaille pour le top 3
            medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, f"#{rank}")

            # Étoile pour les joueurs réguliers
            is_regular = player.name.lower().strip() in self._regular_pseudos
            star = "⭐ " if is_regular else ""

            checkbox = QCheckBox(f"{medal}  {star}{player.name} ({player.score} pts)")
            checkbox.setObjectName("RewardCheckbox")
            checkbox.setChecked(player.reward_claimed)

            self._checkboxes[player.id] = checkbox
            row_layout.addWidget(checkbox)

            content_layout.addWidget(row)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Boutons
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        cancel_btn = QPushButton("Annuler")
        cancel_btn.setObjectName("CancelButton")
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Enregistrer")
        save_btn.setObjectName("LaunchPrimaryButton")
        save_btn.clicked.connect(self.accept)

        buttons_layout.addWidget(cancel_btn)
        buttons_layout.addWidget(save_btn)
        layout.addLayout(buttons_layout)

    def _apply_changes(self):
        """Applique les changements aux joueurs."""
        for player in self._tournament.players:
            checkbox = self._checkboxes.get(player.id)
            if checkbox:
                player.reward_claimed = checkbox.isChecked()

    def exec(self) -> int:
        """Exécute le dialog et retourne si des changements ont été faits."""
        result = super().exec()
        if result:
            self._apply_changes()
            return True
        return False


class TournamentDetailDialog(QDialog):
    """Dialog affichant les détails complets d'un tournoi archivé."""

    def __init__(self, parent, tournament: Tournament):
        super().__init__(parent)

        self._tournament = tournament
        is_commander = "Commander" in tournament.format

        self.setWindowTitle(f"Détails — {tournament.name}")
        self.setModal(True)
        self.setMinimumSize(700, 550)
        self.setObjectName("HistoricDialog")

        self._build_ui(is_commander)

    def _build_ui(self, is_commander: bool):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)

        t = self._tournament

        # Header
        title = QLabel(f"📋 {t.name}")
        title.setObjectName("DialogTitle")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        meta = QLabel(f"{t.format} • {t.date} • {len(t.players)} joueurs • {len(t.rounds)} rounds")
        meta.setAlignment(Qt.AlignCenter)
        meta.setStyleSheet("color: #b6dcd0; font-size: 13px;")
        layout.addWidget(meta)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(20)

        # === CLASSEMENT FINAL ===
        ranking_title = QLabel("🏆 Classement final")
        ranking_title.setObjectName("StatsSectionTitle")
        content_layout.addWidget(ranking_title)

        ranked_players = sorted(
            t.players,
            key=lambda p: (-p.score, -p.robustness, p.name)
        )

        cols = ["#", "Joueur", "Points"]
        if is_commander:
            cols.append("Commandant")

        ranking_table = QTableWidget()
        ranking_table.setObjectName("MatchupsTable")
        ranking_table.setColumnCount(len(cols))
        ranking_table.setHorizontalHeaderLabels(cols)
        ranking_table.setRowCount(len(ranked_players))
        ranking_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        ranking_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        ranking_table.verticalHeader().setVisible(False)
        ranking_table.setShowGrid(False)
        ranking_table.setMaximumHeight(min(40 + len(ranked_players) * 32, 300))

        header = ranking_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Fixed)
        ranking_table.setColumnWidth(0, 50)
        ranking_table.setColumnWidth(2, 80)
        if is_commander:
            header.setSectionResizeMode(3, QHeaderView.Stretch)

        for row, player in enumerate(ranked_players):
            rank = row + 1
            rank_text = {1: "🥇", 2: "🥈", 3: "🥉"}.get(rank, str(rank))

            items = [
                (rank_text, Qt.AlignCenter),
                (player.name, Qt.AlignLeft | Qt.AlignVCenter),
                (str(player.score), Qt.AlignCenter),
            ]
            if is_commander:
                items.append((player.commander or "—", Qt.AlignLeft | Qt.AlignVCenter))

            for col, (text, alignment) in enumerate(items):
                item = QTableWidgetItem(text)
                item.setTextAlignment(alignment)
                if rank == 1:
                    item.setForeground(Qt.GlobalColor.yellow)
                elif rank == 2:
                    item.setForeground(Qt.GlobalColor.lightGray)
                elif rank == 3:
                    item.setForeground(Qt.GlobalColor.darkYellow)
                ranking_table.setItem(row, col, item)

        content_layout.addWidget(ranking_table)

        # === ROUNDS ===
        for rnd in t.rounds:
            round_title = QLabel(f"⚔️ Round {rnd.number}")
            round_title.setObjectName("StatsSectionTitle")
            content_layout.addWidget(round_title)

            for table in rnd.tables:
                card = QFrame()
                card.setObjectName("HistoryCard")
                card_layout = QVBoxLayout(card)
                card_layout.setContentsMargins(12, 10, 12, 10)
                card_layout.setSpacing(6)

                # Titre table
                is_bye = len(table.players) == 1
                if is_bye:
                    table_label = QLabel(f"Table {table.number} (Bye)")
                else:
                    table_label = QLabel(f"Table {table.number}")
                table_label.setStyleSheet("font-weight: bold; font-size: 13px; color: #3ad68a;")
                card_layout.addWidget(table_label)

                # Joueurs de la table
                table_players = list(table.players)
                if table.finished and table.results:
                    table_players.sort(key=lambda p: table.results.get(p.id, 99))

                for player in table_players:
                    position = table.results.get(player.id, None) if table.finished else None

                    parts = []

                    # Position / résultat
                    if is_bye:
                        parts.append("🔹 Bye")
                    elif position is not None:
                        if position == 1:
                            parts.append("🏆")
                        else:
                            parts.append(f"#{position}")
                    else:
                        parts.append("•")

                    parts.append(player.name)

                    if is_commander and player.commander:
                        parts.append(f"  |  {player.commander}")

                    player_row = QHBoxLayout()
                    player_label = QLabel("  ".join(parts[:2]))

                    if position == 1 and not is_bye:
                        player_label.setStyleSheet("color: #f1c40f; font-weight: bold;")
                    elif is_bye:
                        player_label.setStyleSheet("color: #b6dcd0;")

                    player_row.addWidget(player_label)

                    if is_commander and player.commander:
                        cmd_label = QLabel(player.commander)
                        cmd_label.setStyleSheet("color: #8ab4a0; font-style: italic;")
                        cmd_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        player_row.addStretch()
                        player_row.addWidget(cmd_label)

                    card_layout.addLayout(player_row)

                content_layout.addWidget(card)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Bouton fermer
        close_btn = QPushButton("Fermer")
        close_btn.setObjectName("CancelButton")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)
