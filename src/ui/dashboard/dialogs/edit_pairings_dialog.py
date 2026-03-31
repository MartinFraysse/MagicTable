from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QScrollArea, QWidget
)
from PySide6.QtCore import Qt

from core.round import Round
from core.table import Table


class EditPairingsDialog(QDialog):
    """
    Dialog permettant de modifier manuellement les pairings du round 1.
    Sélectionner deux joueurs (tables différentes) puis cliquer Échanger.
    """

    def __init__(self, parent, round_: Round):
        super().__init__(parent)
        self.setWindowTitle("Modifier les pairings — Round 1")
        self.setObjectName("EditPairingsDialog")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setMinimumWidth(560)
        self.setMinimumHeight(460)
        self.setModal(True)

        self._round = round_

        # Copie de travail : table_number -> [Player, ...]
        self._assignment: dict[int, list] = {
            t.number: list(t.players)
            for t in round_.tables
        }

        # Sélection courante : liste de (table_number, player_id)
        self._selected: list[tuple[int, int]] = []

        # player_id -> QPushButton
        self._player_btns: dict[int, QPushButton] = {}

        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(18, 18, 18, 18)

        # --- Bandeau d'instruction ---
        info_banner = QFrame()
        info_banner.setObjectName("EditPairingsInfoBanner")
        info_banner.setAttribute(Qt.WA_StyledBackground, True)
        info_inner = QHBoxLayout(info_banner)
        info_inner.setContentsMargins(12, 10, 12, 10)
        info_inner.setSpacing(10)

        info_icon = QLabel("ℹ")
        info_icon.setObjectName("EditPairingsInfoIcon")
        info_icon.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        info_icon.setFixedWidth(18)
        info_inner.addWidget(info_icon)

        info_text = QLabel(
            "Cliquez sur deux joueurs de <b>tables différentes</b> pour les échanger. "
            "Vous pouvez aussi changer qui reçoit le BYE."
        )
        info_text.setObjectName("EditPairingsInfo")
        info_text.setWordWrap(True)
        info_inner.addWidget(info_text, 1)

        layout.addWidget(info_banner)

        # --- Barre d'état de sélection ---
        self._sel_frame = QFrame()
        self._sel_frame.setObjectName("EditPairingsSelStatus")
        self._sel_frame.setAttribute(Qt.WA_StyledBackground, True)
        sel_inner = QHBoxLayout(self._sel_frame)
        sel_inner.setContentsMargins(12, 8, 12, 8)
        sel_inner.setSpacing(8)

        self._sel_icon = QLabel("○")
        self._sel_icon.setObjectName("EditPairingsSelIcon")
        self._sel_icon.setFixedWidth(18)
        self._sel_icon.setAlignment(Qt.AlignVCenter | Qt.AlignHCenter)
        sel_inner.addWidget(self._sel_icon)

        self._sel_label = QLabel("Aucun joueur sélectionné")
        self._sel_label.setObjectName("EditPairingsSelLabel")
        sel_inner.addWidget(self._sel_label, 1)

        # Initialiser la propriété de state
        for w in (self._sel_frame, self._sel_icon, self._sel_label):
            w.setProperty("selState", "empty")

        layout.addWidget(self._sel_frame)

        # --- Zone scrollable avec les tables ---
        scroll = QScrollArea()
        scroll.setObjectName("EditPairingsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self._content = QWidget()
        self._content.setObjectName("EditPairingsContent")
        self._content.setAttribute(Qt.WA_StyledBackground, True)
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setSpacing(6)
        self._content_layout.setContentsMargins(0, 2, 0, 2)

        self._rebuild_tables_ui()

        scroll.setWidget(self._content)
        layout.addWidget(scroll, 1)

        # --- Bouton échanger ---
        self._swap_btn = QPushButton("⇄  Échanger les deux joueurs sélectionnés")
        self._swap_btn.setObjectName("EditPairingsSwapBtn")
        self._swap_btn.setEnabled(False)
        self._swap_btn.setMinimumHeight(40)
        self._swap_btn.clicked.connect(self._do_swap)
        layout.addWidget(self._swap_btn)

        # --- Confirmer / Annuler ---
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        cancel_btn = QPushButton("Annuler")
        cancel_btn.setObjectName("SecondaryButton")
        cancel_btn.setMinimumHeight(38)
        cancel_btn.clicked.connect(self.reject)

        ok_btn = QPushButton("Confirmer les pairings")
        ok_btn.setObjectName("PrimaryButton")
        ok_btn.setMinimumHeight(38)
        ok_btn.clicked.connect(self.accept)

        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        layout.addLayout(btn_row)

    def _rebuild_tables_ui(self):
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._player_btns.clear()
        selected_ids = {pid for _, pid in self._selected}

        for table_num in sorted(self._assignment.keys()):
            players = self._assignment[table_num]
            is_bye = len(players) == 1

            row = QFrame()
            row.setObjectName("EditPairingsByeRow" if is_bye else "EditPairingsRow")
            row.setAttribute(Qt.WA_StyledBackground, True)
            row_layout = QHBoxLayout(row)
            row_layout.setSpacing(8)
            row_layout.setContentsMargins(10, 8, 10, 8)

            # --- Badge Table N / BYE ---
            badge = QFrame()
            badge.setObjectName("EditPairingsByeBadge" if is_bye else "EditPairingsTableBadge")
            badge.setAttribute(Qt.WA_StyledBackground, True)
            badge.setFixedWidth(56)
            badge_layout = QVBoxLayout(badge)
            badge_layout.setContentsMargins(4, 4, 4, 4)
            badge_layout.setSpacing(0)
            badge_layout.setAlignment(Qt.AlignCenter)

            if is_bye:
                bye_lbl = QLabel("BYE")
                bye_lbl.setObjectName("EditPairingsBadgeLabel")
                bye_lbl.setAlignment(Qt.AlignCenter)
                badge_layout.addWidget(bye_lbl)
            else:
                top_lbl = QLabel("TABLE")
                top_lbl.setObjectName("EditPairingsBadgeTop")
                top_lbl.setAlignment(Qt.AlignCenter)
                badge_layout.addWidget(top_lbl)

                num_lbl = QLabel(str(table_num))
                num_lbl.setObjectName("EditPairingsBadgeNum")
                num_lbl.setAlignment(Qt.AlignCenter)
                badge_layout.addWidget(num_lbl)

            row_layout.addWidget(badge)

            # --- Séparateur vertical ---
            sep = QFrame()
            sep.setObjectName("EditPairingsSep")
            sep.setFrameShape(QFrame.VLine)
            row_layout.addWidget(sep)

            # --- Boutons joueurs avec "vs" entre eux ---
            for i, player in enumerate(players):
                if i > 0:
                    vs_lbl = QLabel("vs")
                    vs_lbl.setObjectName("EditPairingsVsLabel")
                    vs_lbl.setAlignment(Qt.AlignCenter)
                    vs_lbl.setFixedWidth(24)
                    row_layout.addWidget(vs_lbl)

                btn = QPushButton(player.name)
                btn.setObjectName("EditPairingsPlayerBtn")
                btn.setCheckable(True)
                btn.setChecked(player.id in selected_ids)
                btn.setMinimumHeight(36)

                btn.clicked.connect(
                    lambda checked, t=table_num, p=player: self._toggle_player(t, p.id)
                )
                self._player_btns[player.id] = btn
                row_layout.addWidget(btn, 1)

            if is_bye:
                hint = QLabel("victoire auto")
                hint.setObjectName("EditPairingsHint")
                row_layout.addWidget(hint)

            self._content_layout.addWidget(row)

        self._content_layout.addStretch()

    # ------------------------------------------------------------------
    # Sélection
    # ------------------------------------------------------------------
    def _toggle_player(self, table_num: int, player_id: int):
        entry = (table_num, player_id)

        if entry in self._selected:
            self._selected.remove(entry)
        else:
            if len(self._selected) >= 2:
                old = self._selected.pop(0)
                old_btn = self._player_btns.get(old[1])
                if old_btn:
                    old_btn.setChecked(False)
            self._selected.append(entry)

        self._refresh_selection_ui()

    def _apply_sel_state(self, state: str):
        for w in (self._sel_frame, self._sel_icon, self._sel_label):
            w.setProperty("selState", state)
            w.style().unpolish(w)
            w.style().polish(w)

    def _refresh_selection_ui(self):
        selected_ids = {pid for _, pid in self._selected}
        for pid, btn in self._player_btns.items():
            btn.setChecked(pid in selected_ids)

        if len(self._selected) == 0:
            self._apply_sel_state("empty")
            self._sel_icon.setText("○")
            self._sel_label.setText("Aucun joueur sélectionné")
            self._swap_btn.setEnabled(False)

        elif len(self._selected) == 1:
            t, pid = self._selected[0]
            player = next((p for p in self._assignment[t] if p.id == pid), None)
            name = player.name if player else "?"
            table_label = "BYE" if len(self._assignment[t]) == 1 else f"Table {t}"
            self._apply_sel_state("one")
            self._sel_icon.setText("◉")
            self._sel_label.setText(f"{name}  ({table_label})  —  Sélectionnez un second joueur")
            self._swap_btn.setEnabled(False)

        else:
            t1, pid1 = self._selected[0]
            t2, pid2 = self._selected[1]
            p1 = next((p for p in self._assignment[t1] if p.id == pid1), None)
            p2 = next((p for p in self._assignment[t2] if p.id == pid2), None)
            name1 = p1.name if p1 else "?"
            name2 = p2.name if p2 else "?"
            lbl1 = "BYE" if len(self._assignment[t1]) == 1 else f"Table {t1}"
            lbl2 = "BYE" if len(self._assignment[t2]) == 1 else f"Table {t2}"

            if t1 == t2:
                self._apply_sel_state("error")
                self._sel_icon.setText("⚠")
                self._sel_label.setText("Les deux joueurs sont dans la même table")
                self._swap_btn.setEnabled(False)
            else:
                self._apply_sel_state("ready")
                self._sel_icon.setText("⇄")
                self._sel_label.setText(
                    f"{name1}  ({lbl1})  ↔  {name2}  ({lbl2})"
                )
                self._swap_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # Échange
    # ------------------------------------------------------------------
    def _do_swap(self):
        if len(self._selected) < 2:
            return

        t1, pid1 = self._selected[0]
        t2, pid2 = self._selected[1]

        if t1 == t2:
            return

        players1 = self._assignment[t1]
        players2 = self._assignment[t2]

        p1 = next((p for p in players1 if p.id == pid1), None)
        p2 = next((p for p in players2 if p.id == pid2), None)

        if not p1 or not p2:
            return

        players1[players1.index(p1)] = p2
        players2[players2.index(p2)] = p1

        self._selected.clear()
        self._rebuild_tables_ui()
        self._refresh_selection_ui()

    # ------------------------------------------------------------------
    # Résultat
    # ------------------------------------------------------------------
    def get_updated_tables(self) -> list[Table]:
        """Retourne les nouvelles tables. Les BYE (1 joueur) sont marquées finished."""
        result = []
        for table in self._round.tables:
            new_players = self._assignment.get(table.number, table.players)
            if len(new_players) == 1:
                result.append(Table(
                    number=table.number,
                    players=new_players,
                    finished=True,
                    results={new_players[0].id: 1},
                ))
            else:
                result.append(Table(
                    number=table.number,
                    players=new_players,
                ))
        return result
