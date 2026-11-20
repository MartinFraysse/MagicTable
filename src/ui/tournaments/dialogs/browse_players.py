"""Dialog de sélection des joueurs réguliers à inscrire au tournoi."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QDialog, QListWidgetItem, QLineEdit, QVBoxLayout, QLabel, QPushButton, QListWidget
)


class BrowsePlayersDialog(QDialog):
    """Dialog pour parcourir et ajouter directement des joueurs permanents au tournoi."""

    def __init__(self, parent, regular_players: list, tournament):
        super().__init__(parent)
        self.setWindowTitle("Joueurs permanents")
        self.setModal(True)
        self.setObjectName("BrowsePlayersDialog")
        self.setFixedSize(400, 480)
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
        """Retourne {nom_lowercase: player_id} pour les joueurs actifs (non dropped)."""
        return {p.name.lower().strip(): p.id for p in self._tournament.players if not p.dropped}

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
            # UserRole = pseudo, UserRole+1 = tournament player_id si inscrit, UserRole+2 = regular_player.id
            item.setData(Qt.UserRole, player.pseudo)
            item.setData(Qt.UserRole + 1, player_id)
            item.setData(Qt.UserRole + 2, player.id)
            self.list_widget.addItem(item)

    def _on_item_clicked(self, item: QListWidgetItem):
        pseudo = item.data(Qt.UserRole)
        player_id = item.data(Qt.UserRole + 1)
        rp_id = item.data(Qt.UserRole + 2)
        if player_id is not None:
            # Déjà inscrit → retirer du tournoi
            self._tournament.remove_player(player_id)
        else:
            # Pas encore inscrit → ajouter avec le lien explicite
            self._tournament.add_player(pseudo, regular_player_id=rp_id)
        self._refresh_list()

    def _add_player(self, name: str):
        self._tournament.add_player(name)
        self._refresh_list()
