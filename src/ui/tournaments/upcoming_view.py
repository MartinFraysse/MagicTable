from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal

from core.tournament import (
    Tournament,
    next_free_tournament_id,
    sort_tournaments_by_date,
    )
from ui.widgets.tournament_card import TournamentCard
from ui.tournaments.dialogs.create_tournament import CreateTournamentDialog
from storage.tournaments import TournamentStorage
from datetime import datetime


class UpcomingView(QWidget):
    """
    Vue des tournois à venir.
    """

    # 🔗 Signal vers TournamentViewMain
    launch_requested = Signal(Tournament)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("UpcomingView")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFocusPolicy(Qt.StrongFocus)

        # Carte actuellement sélectionnée
        self._selected_card: TournamentCard | None = None

        # =========================
        # Données (OBJETS METIER UNIQUEMENT)
        # =========================
        self._tournaments: list[Tournament] = []
        self._tournament_ids: dict[int, str] = {}
        self._cards_by_id: dict[int, TournamentCard] = {}

        self._build_ui()
        self._load_tournaments_from_storage()

    # ======================================================
    # PUBLIC API (pour LaunchView)
    # ======================================================
    def get_tournament_by_id(self, tournament_id: int) -> Tournament | None:
        for t in self._tournaments:
            if t.id == tournament_id:
                return t
        return None

    # ======================================================
    # UI
    # ======================================================
    def _build_ui(self):
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(16)

        # ---------- Header ----------
        header = QFrame()
        header.setObjectName("UpcomingHeader")
        header.setAttribute(Qt.WA_StyledBackground, True)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("⏳ Tournois à venir")
        title.setObjectName("UpcomingTitle")

        add_btn = QPushButton("➕  Nouveau tournoi")
        add_btn.setObjectName("UpcomingPrimaryButton")
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self._open_create_dialog)

        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(add_btn)

        self.root_layout.addWidget(header)

        # ---------- Scroll ----------
        scroll = QScrollArea()
        scroll.setObjectName("UpcomingScrollArea")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        content.setObjectName("UpcomingContent")
        content.setAttribute(Qt.WA_StyledBackground, True)

        self.cards_layout = QVBoxLayout(content)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(12)
        self.cards_layout.addStretch()

        scroll.setWidget(content)

        scroll_container = QFrame()
        scroll_container.setObjectName("UpcomingScrollContainer")
        scroll_container.setAttribute(Qt.WA_StyledBackground, True)

        scroll_container_layout = QVBoxLayout(scroll_container)
        scroll_container_layout.setContentsMargins(12, 12, 12, 12)
        scroll_container_layout.addWidget(scroll)

        self.root_layout.addWidget(scroll_container, 1)

    # ======================================================
    # Create / Edit
    # ======================================================
    def _open_create_dialog(self):
        dialog = CreateTournamentDialog(self)

        if not dialog.exec():
            return

        tid = next_free_tournament_id(self._tournaments)
        tournament = Tournament.create_tournament(
            tournament_id=tid,
            name=dialog.name_input.text(),
            format=dialog.format_input.currentText(),
            date=dialog.date_input.text(),
            max_rounds=dialog.get_max_rounds(),
        )


        self._tournaments.append(tournament)
        self._register_tournament(tournament)

        self._tournaments = sort_tournaments_by_date(self._tournaments)
        self._rebuild_cards_layout()
        self._save_all()

    def _register_tournament(self, tournament: Tournament):
        tid = tournament.id
        self._tournament_ids[tid] = tournament.name

        card = TournamentCard(tournament, self)
        self._cards_by_id[tid] = card

        card.request_edit.connect(
            lambda t=tournament, c=card: self._edit_tournament(c, t)
        )
        card.request_launch.connect(self._send_to_launch)
        card.request_delete.connect(
            lambda t=tournament, c=card: self._delete_tournament(c, t)
        )
        card.card_selected.connect(self._on_card_selected)

        self.cards_layout.insertWidget(
            self.cards_layout.count() - 1,
            card
        )

    def _edit_tournament(self, card: TournamentCard, tournament: Tournament):
        dialog = CreateTournamentDialog(self, tournament=tournament)

        if not dialog.exec():
            return

        dialog.apply_changes()

        self._tournaments = sort_tournaments_by_date(self._tournaments)
        self._rebuild_cards_layout()
        card._refresh()
        self._save_all()

    def _delete_tournament(self, card: TournamentCard, tournament: Tournament):
        reply = QMessageBox.question(
            self,
            "Supprimer le tournoi",
            f"Supprimer définitivement « {tournament.name} » ?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        tid = tournament.id

        self._tournaments = [t for t in self._tournaments if t.id != tid]
        self._tournament_ids.pop(tid, None)
        self._cards_by_id.pop(tid, None)

        self.cards_layout.removeWidget(card)
        card.deleteLater()

        if self._selected_card == card:
            self._selected_card = None

        self._save_all()

    # ======================================================
    # Launch
    # ======================================================
    def _send_to_launch(self, tournament: Tournament):
        self.launch_requested.emit(tournament)

    def hide_tournament_card(self, tournament_id: int):
        card = self._cards_by_id.get(tournament_id)
        if card:
            card.hide()

    def show_tournament_card(self, tournament_id: int):
        card = self._cards_by_id.get(tournament_id)
        if not card:
            return

        # 🔑 Désélection complète (visuelle + logique)
        card.setProperty("selected", False)
        card.style().unpolish(card)
        card.style().polish(card)

        if self._selected_card == card:
            self._selected_card = None

        card.show()
        card._refresh()

    def remove_archived_tournament(self, tournament_id: int):
        """Retire la carte d'un tournoi archivé."""
        card = self._cards_by_id.get(tournament_id)
        if card:
            self.cards_layout.removeWidget(card)
            card.deleteLater()
            self._cards_by_id.pop(tournament_id, None)
            self._tournament_ids.pop(tournament_id, None)

            if self._selected_card == card:
                self._selected_card = None

        self._tournaments = sort_tournaments_by_date(self._tournaments)
        self._rebuild_cards_layout()
        self._save_all()


    def refresh_tournament(self, tournament: Tournament):
        card = self._cards_by_id.get(tournament.id)
        if card:
            card._refresh()

        self._tournaments = sort_tournaments_by_date(self._tournaments)
        self._rebuild_cards_layout()
        self._save_all()

    # ======================================================
    # Storage
    # ======================================================
    def _load_tournaments_from_storage(self):
        raw = TournamentStorage.load()
        self._tournaments.clear()

        for data in raw:
            tournament = Tournament.from_dict(data)
            self._tournaments.append(tournament)
            # Ne créer une carte que pour les tournois non archivés
            if not tournament.archived:
                self._register_tournament(tournament)

        self._tournaments = sort_tournaments_by_date(self._tournaments)
        self._rebuild_cards_layout()

    def _save_all(self):
        TournamentStorage.save([t.to_dict() for t in self._tournaments])

    # ======================================================
    # Sorting
    # ======================================================
    def _rebuild_cards_layout(self):
        for card in self._cards_by_id.values():
            self.cards_layout.removeWidget(card)

        for tournament in self._tournaments:
            # Ne pas afficher les tournois archivés
            if tournament.archived:
                continue
            card = self._cards_by_id.get(tournament.id)
            if card:
                self.cards_layout.insertWidget(
                    self.cards_layout.count() - 1,
                    card
                )

    # ======================================================
    # Selection & Keyboard
    # ======================================================
    def _on_card_selected(self, card: TournamentCard):
        if self._selected_card:
            self._selected_card.setProperty("selected", False)
            self._selected_card.style().unpolish(self._selected_card)
            self._selected_card.style().polish(self._selected_card)

        self._selected_card = card
        card.setProperty("selected", True)
        card.style().unpolish(card)
        card.style().polish(card)

        self.setFocus()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete and self._selected_card:
            tournament = self._selected_card.tournament
            self._delete_tournament(self._selected_card, tournament)
            event.accept()
            return

        super().keyPressEvent(event)
