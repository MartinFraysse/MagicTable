"""Vue principale de la page Ligue."""

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QFrame,
    QLabel, QPushButton, QScrollArea,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QSizePolicy, QMessageBox,
)
from PySide6.QtCore import Qt

from core.league import League, compute_league_standings
from core.tournament import Tournament
from storage.leagues import LeagueStorage
from storage.tournaments import TournamentStorage
from ui.league.dialogs.create_league_dialog import CreateLeagueDialog
from ui.league.dialogs.add_tournament_dialog import AddTournamentDialog
from ui.league.dialogs.player_detail_dialog import PlayerDetailDialog
from ui.tournaments.historic_view import TournamentDetailDialog


class LeagueViewMain(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName("LeagueViewMain")

        self._leagues: list[League] = []
        self._tournaments: list[Tournament] = []
        self._selected: League | None = None

        self._build_ui()
        self.refresh()

    # ── Construction UI ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(20)
        root.addWidget(self._build_left_panel(), 0)
        root.addWidget(self._build_right_panel(), 1)

    # ── Panneau gauche ────────────────────────────────────────────────────────

    def _build_left_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("LeagueLeftPanel")
        frame.setFixedWidth(270)
        frame.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title = QLabel("Ligues")
        title.setObjectName("LeaguePanelTitle")

        new_btn = QPushButton("+  Nouvelle ligue")
        new_btn.setObjectName("PrimaryButton")
        new_btn.setMinimumHeight(40)
        new_btn.clicked.connect(self._on_create)

        layout.addWidget(title)
        layout.addWidget(new_btn)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._list_container = QWidget()
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(0, 4, 4, 0)
        self._list_layout.setSpacing(8)
        self._list_layout.addStretch()

        scroll.setWidget(self._list_container)
        layout.addWidget(scroll)

        return frame

    # ── Panneau droit ─────────────────────────────────────────────────────────

    def _build_right_panel(self) -> QFrame:
        frame = QFrame()
        frame.setObjectName("LeagueRightPanel")
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # État vide
        self._empty_widget = self._build_empty_state()
        layout.addWidget(self._empty_widget)

        # Détail
        self._detail_widget = self._build_detail_widget()
        self._detail_widget.hide()
        layout.addWidget(self._detail_widget, 1)

        return frame

    def _build_empty_state(self) -> QWidget:
        w = QWidget()
        w.setAttribute(Qt.WA_StyledBackground, True)
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)

        icon = QLabel("🏅")
        icon.setObjectName("LeagueEmptyIcon")
        icon.setAlignment(Qt.AlignCenter)

        lbl = QLabel("Sélectionnez une ligue\nou créez-en une nouvelle.")
        lbl.setObjectName("LeagueEmptyLabel")
        lbl.setAlignment(Qt.AlignCenter)

        layout.addWidget(icon)
        layout.addWidget(lbl)
        return w

    def _build_detail_widget(self) -> QWidget:
        widget = QWidget()
        widget.setAttribute(Qt.WA_StyledBackground, True)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        # ── En-tête ──────────────────────────────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(10)

        self._detail_title = QLabel("")
        self._detail_title.setObjectName("LeagueDetailTitle")

        self._detail_subtitle = QLabel("")
        self._detail_subtitle.setObjectName("LeagueDetailSubtitle")

        title_col = QVBoxLayout()
        title_col.setSpacing(3)
        title_col.addWidget(self._detail_title)
        title_col.addWidget(self._detail_subtitle)

        edit_btn = QPushButton("Modifier")
        edit_btn.setObjectName("SecondaryButton")
        edit_btn.setMinimumWidth(100)
        edit_btn.setFixedHeight(36)
        edit_btn.clicked.connect(self._on_edit)

        delete_btn = QPushButton("Supprimer")
        delete_btn.setObjectName("DangerButton")
        delete_btn.setMinimumWidth(100)
        delete_btn.setFixedHeight(36)
        delete_btn.clicked.connect(self._on_delete)

        header.addLayout(title_col)
        header.addStretch()
        header.addWidget(edit_btn)
        header.addWidget(delete_btn)
        layout.addLayout(header)

        # ── Classement ───────────────────────────────────────────────────────
        standings_title = QLabel("Classement")
        standings_title.setObjectName("LeagueSectionTitle")
        layout.addWidget(standings_title)

        self._standings_table = QTableWidget(0, 5)
        self._standings_table.setObjectName("LeagueStandingsTable")
        self._standings_table.setHorizontalHeaderLabels(
            ["#", "Joueur", "Points", "Tournois", "Meilleur"]
        )
        hh = self._standings_table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        hh.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self._standings_table.verticalHeader().setVisible(False)
        self._standings_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._standings_table.setSelectionMode(QTableWidget.NoSelection)
        self._standings_table.setAlternatingRowColors(True)
        self._standings_table.setCursor(Qt.PointingHandCursor)
        self._standings_table.cellClicked.connect(self._on_standing_clicked)
        layout.addWidget(self._standings_table, 1)

        # ── Tournois inclus ───────────────────────────────────────────────────
        t_header = QHBoxLayout()
        t_title = QLabel("Tournois inclus")
        t_title.setObjectName("LeagueSectionTitle")
        add_t_btn = QPushButton("+ Ajouter un tournoi")
        add_t_btn.setObjectName("PrimaryButton")
        add_t_btn.setFixedHeight(34)
        add_t_btn.clicked.connect(self._on_add_tournament)
        t_header.addWidget(t_title)
        t_header.addStretch()
        t_header.addWidget(add_t_btn)
        layout.addLayout(t_header)

        scroll = QScrollArea()
        scroll.setObjectName("LeagueTournamentsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setFixedHeight(130)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._t_list_widget = QWidget()
        self._t_list_layout = QVBoxLayout(self._t_list_widget)
        self._t_list_layout.setContentsMargins(0, 0, 4, 0)
        self._t_list_layout.setSpacing(6)
        self._t_list_layout.addStretch()

        scroll.setWidget(self._t_list_widget)
        layout.addWidget(scroll)

        return widget

    # ── Données ───────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        raw_leagues = LeagueStorage.load()
        self._leagues = [League.from_dict(d) for d in raw_leagues]

        raw_t = TournamentStorage.load()
        self._tournaments = [Tournament.from_dict(d) for d in raw_t]

        self._rebuild_league_list()

        if self._selected:
            updated = next((lg for lg in self._leagues if lg.id == self._selected.id), None)
            if updated:
                self._selected = updated
                self._show_detail(updated)
            else:
                self._selected = None
                self._show_empty()

    def _save(self) -> None:
        LeagueStorage.save([lg.to_dict() for lg in self._leagues])

    # ── Liste gauche ──────────────────────────────────────────────────────────

    def _rebuild_league_list(self) -> None:
        while self._list_layout.count() > 1:
            item = self._list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for league in self._leagues:
            card = self._make_league_card(league)
            self._list_layout.insertWidget(self._list_layout.count() - 1, card)

    def _make_league_card(self, league: League) -> QFrame:
        is_selected = self._selected and self._selected.id == league.id

        card = QFrame()
        card.setObjectName("LeagueCard")
        card.setCursor(Qt.PointingHandCursor)
        if is_selected:
            card.setProperty("selected", True)

        outer = QHBoxLayout(card)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Barre d'accent verticale gauche
        accent = QFrame()
        accent.setObjectName("LeagueCardAccent")
        accent.setFixedWidth(4)
        outer.addWidget(accent)

        inner = QVBoxLayout()
        inner.setContentsMargins(12, 10, 12, 10)
        inner.setSpacing(3)

        name_lbl = QLabel(league.name)
        name_lbl.setObjectName("LeagueCardName")

        format_lbl = QLabel(league.format)
        format_lbl.setObjectName("LeagueCardFormat")

        meta = f"Saison {league.season}  •  {len(league.tournament_ids)} tournoi(s)"
        meta_lbl = QLabel(meta)
        meta_lbl.setObjectName("LeagueCardMeta")

        inner.addWidget(name_lbl)
        inner.addWidget(format_lbl)
        inner.addWidget(meta_lbl)
        outer.addLayout(inner)

        card.mousePressEvent = lambda _e, lg=league: self._on_select(lg)
        return card

    # ── Panneau droit ─────────────────────────────────────────────────────────

    def _show_empty(self) -> None:
        self._empty_widget.show()
        self._detail_widget.hide()

    def _show_detail(self, league: League) -> None:
        self._empty_widget.hide()
        self._detail_widget.show()

        self._detail_title.setText(league.name)
        self._detail_subtitle.setText(f"{league.format}  •  Saison {league.season}")

        self._refresh_standings(league)
        self._refresh_tournament_list(league)

    def _refresh_standings(self, league: League) -> None:
        entries = compute_league_standings(league, self._tournaments)
        self._current_entries = entries
        self._standings_table.setSpan(0, 0, 1, 1)  # reset tout span précédent
        self._standings_table.setRowCount(len(entries))

        medals = {1: "🥇", 2: "🥈", 3: "🥉"}

        for row, entry in enumerate(entries):
            rank_str  = medals.get(entry.rank, str(entry.rank))
            best_str  = medals.get(entry.best_result, f"#{entry.best_result}")

            for col, (val, align) in enumerate([
                (rank_str,                      Qt.AlignCenter),
                (entry.player_name,             Qt.AlignLeft | Qt.AlignVCenter),
                (f"{entry.total_points} pts",   Qt.AlignCenter),
                (str(entry.tournaments_played), Qt.AlignCenter),
                (best_str,                      Qt.AlignCenter),
            ]):
                item = QTableWidgetItem(val)
                item.setTextAlignment(align)
                self._standings_table.setItem(row, col, item)

        if not entries:
            self._standings_table.setRowCount(1)
            placeholder = QTableWidgetItem("Aucune donnée — ajoutez des tournois archivés")
            placeholder.setTextAlignment(Qt.AlignCenter)
            placeholder.setFlags(Qt.NoItemFlags)
            self._standings_table.setItem(0, 0, placeholder)
            self._standings_table.setSpan(0, 0, 1, 5)

    def _refresh_tournament_list(self, league: League) -> None:
        while self._t_list_layout.count() > 1:
            item = self._t_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        t_by_id = {t.id: t for t in self._tournaments}

        if not league.tournament_ids:
            empty = QLabel("Aucun tournoi — cliquez sur \"+ Ajouter un tournoi\".")
            empty.setObjectName("LeagueEmptyLabel")
            empty.setAlignment(Qt.AlignCenter)
            self._t_list_layout.insertWidget(0, empty)
            return

        for tid in league.tournament_ids:
            t = t_by_id.get(tid)
            if t is None:
                continue

            row = QFrame()
            row.setObjectName("LeagueTournamentRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(12, 8, 8, 8)
            row_layout.setSpacing(8)

            col = QVBoxLayout()
            col.setSpacing(2)

            name_lbl = QLabel(t.name)
            name_lbl.setObjectName("LeagueTournamentName")

            meta_lbl = QLabel(f"{t.date}  •  {len(t.players)} joueurs")
            meta_lbl.setObjectName("LeagueTournamentMeta")

            col.addWidget(name_lbl)
            col.addWidget(meta_lbl)

            row.setCursor(Qt.PointingHandCursor)
            row.mouseDoubleClickEvent = lambda _e, _t=t: TournamentDetailDialog(self, _t).exec()

            remove_btn = QPushButton("✕")
            remove_btn.setObjectName("RemoveSmallButton")
            remove_btn.setFixedSize(26, 26)
            remove_btn.setToolTip("Retirer ce tournoi de la ligue")
            remove_btn.clicked.connect(lambda _, _tid=tid: self._on_remove_tournament(_tid))

            row_layout.addLayout(col)
            row_layout.addStretch()
            row_layout.addWidget(remove_btn)

            self._t_list_layout.insertWidget(self._t_list_layout.count() - 1, row)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _on_standing_clicked(self, row: int, _col: int) -> None:
        if not self._selected or not hasattr(self, "_current_entries"):
            return
        if row >= len(self._current_entries):
            return
        entry = self._current_entries[row]
        dialog = PlayerDetailDialog(self, entry, self._selected, self._tournaments)
        dialog.exec()

    def _on_select(self, league: League) -> None:
        self._selected = league
        self._rebuild_league_list()
        self._show_detail(league)

    def _on_create(self) -> None:
        dialog = CreateLeagueDialog(self, self._leagues)
        if not dialog.exec():
            return
        new_league = dialog.build_league()
        self._leagues.append(new_league)
        self._save()
        self._rebuild_league_list()
        self._on_select(new_league)

    def _on_edit(self) -> None:
        if not self._selected:
            return
        dialog = CreateLeagueDialog(self, self._leagues, league=self._selected)
        if not dialog.exec():
            return
        dialog.build_league()
        self._save()
        self._rebuild_league_list()
        self._show_detail(self._selected)

    def _on_delete(self) -> None:
        if not self._selected:
            return
        reply = QMessageBox.question(
            self,
            "Supprimer la ligue",
            f"Supprimer la ligue « {self._selected.name} » ?\n\nLes tournois ne seront pas supprimés.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._leagues = [lg for lg in self._leagues if lg.id != self._selected.id]
        self._selected = None
        self._save()
        self._rebuild_league_list()
        self._show_empty()

    def _on_add_tournament(self) -> None:
        if not self._selected:
            return
        dialog = AddTournamentDialog(self, self._selected, self._tournaments)
        if not dialog.exec():
            return
        tid = dialog.selected_tournament_id()
        if tid is not None and tid not in self._selected.tournament_ids:
            self._selected.tournament_ids.append(tid)
            self._save()
            self._show_detail(self._selected)
            self._rebuild_league_list()

    def _on_remove_tournament(self, tournament_id: int) -> None:
        if not self._selected:
            return
        self._selected.tournament_ids = [
            tid for tid in self._selected.tournament_ids if tid != tournament_id
        ]
        self._save()
        self._show_detail(self._selected)
        self._rebuild_league_list()
