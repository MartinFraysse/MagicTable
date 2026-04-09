from PySide6.QtCore import Qt, QRectF, QRect
from PySide6.QtGui import (
    QPainter, QPixmap, QLinearGradient, QBrush, QColor,
    QPainterPath, QFont, QPen,
)
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QScrollArea, QWidget, QTabWidget,
    QLineEdit, QSizePolicy, QSplitter,
)

from core.commander import Commander, MTG_COLORS, COLOR_HEX, COLOR_SYMBOLS
from storage.base import DATA_DIR
from storage.commanders import CommanderStorage
from storage.tournaments import TournamentStorage


# ---------------------------------------------------------------------------
# Stats computation
# ---------------------------------------------------------------------------

def _final_ranking(t: dict) -> dict[int, int]:
    """
    Retourne {player_id: rang} en tenant compte du bracket s'il est terminé,
    sinon par score Swiss.
    """
    bracket = t.get("bracket") or {}
    matches = bracket.get("matches", [])
    finished = bracket.get("finished", False)

    if finished and matches:
        ranking: dict[int, int] = {}

        # Finale principale (non 3ème place)
        final = next((m for m in matches
                      if m.get("round_name") == "final" and not m.get("is_third_place")), None)
        if final and final.get("finished"):
            w = final["winner_id"]
            p1, p2 = final["player1_id"], final["player2_id"]
            ranking[w] = 1
            ranking[p2 if w == p1 else p1] = 2

        # Match 3ème place
        third = next((m for m in matches if m.get("is_third_place")), None)
        if third and third.get("finished"):
            w = third["winner_id"]
            p1, p2 = third["player1_id"], third["player2_id"]
            ranking[w] = 3
            ranking[p2 if w == p1 else p1] = 4

        # Joueurs Swiss hors bracket (non classés via bracket)
        rank = len(ranking) + 1
        sorted_players = sorted(
            t.get("players", []),
            key=lambda p: (-p.get("score", 0), -p.get("robustness", 0), p.get("name", ""))
        )
        for p in sorted_players:
            if p["id"] not in ranking:
                ranking[p["id"]] = rank
                rank += 1

        return ranking

    # Pas de bracket → classement Swiss
    sorted_players = sorted(
        t.get("players", []),
        key=lambda p: (-p.get("score", 0), -p.get("robustness", 0), p.get("name", ""))
    )
    return {p["id"]: i + 1 for i, p in enumerate(sorted_players)}


def _table_result(pid: int, tbl: dict) -> str:
    """Retourne 'W', 'L' ou 'D' pour un joueur dans une table terminée."""
    results = tbl.get("results", {})
    # Les clés peuvent être int ou str selon la sérialisation JSON
    my_pos = results.get(pid) or results.get(str(pid))
    player_ids = tbl.get("player_ids", [])

    if my_pos == 1:
        return "W"

    # Égalité en 1v1 : aucun joueur n'a la position 1 et les deux ont la même position
    if len(player_ids) == 2 and my_pos is not None:
        other_id = next((x for x in player_ids if x != pid), None)
        other_pos = results.get(other_id) or results.get(str(other_id)) if other_id is not None else None
        if other_pos is not None and other_pos == my_pos:
            return "D"

    return "L"


def _stats_for_tournaments(commander_name: str, tournaments: list) -> dict | None:
    """Calcule les stats d'un commandant sur une liste de tournois. Retourne None si aucun."""
    tournois_joues = 0
    victoires = 0
    podiums = 0
    match_w = match_l = match_d = 0
    joueurs: dict[str, dict] = {}
    matchups: dict[str, dict] = {}
    derniere_date = ""

    for t in tournaments:
        players_with_cmd = [
            p for p in t.get("players", [])
            if p.get("commander", "") == commander_name
        ]
        if not players_with_cmd:
            continue

        tournois_joues += 1
        date = t.get("date", "")
        if date > derniere_date:
            derniere_date = date

        rank_by_id = _final_ranking(t)
        bracket_matches = (t.get("bracket") or {}).get("matches", [])
        pid_to_commander = {p["id"]: p.get("commander", "") for p in t.get("players", [])}

        for p in players_with_cmd:
            name = p.get("name", "?")
            pid = p.get("id")

            pw = pl = pd = 0
            for r in t.get("rounds", []):
                for tbl in r.get("tables", []):
                    if pid not in tbl.get("player_ids", []) or not tbl.get("finished"):
                        continue
                    res = _table_result(pid, tbl)
                    if res == "W":   pw += 1
                    elif res == "D": pd += 1
                    else:            pl += 1
                    for opp_id in tbl.get("player_ids", []):
                        if opp_id == pid:
                            continue
                        opp_cmd = pid_to_commander.get(opp_id, "")
                        if not opp_cmd:
                            continue
                        if opp_cmd not in matchups:
                            matchups[opp_cmd] = {"w": 0, "l": 0, "d": 0}
                        if res == "W":   matchups[opp_cmd]["w"] += 1
                        elif res == "D": matchups[opp_cmd]["d"] += 1
                        else:            matchups[opp_cmd]["l"] += 1

            for m in bracket_matches:
                if not m.get("finished") or pid not in (m.get("player1_id"), m.get("player2_id")):
                    continue
                if m.get("winner_id") == pid: pw += 1
                else:                          pl += 1
                opp_id = m.get("player2_id") if m.get("player1_id") == pid else m.get("player1_id")
                opp_cmd = pid_to_commander.get(opp_id, "")
                if opp_cmd:
                    if opp_cmd not in matchups:
                        matchups[opp_cmd] = {"w": 0, "l": 0, "d": 0}
                    if m.get("winner_id") == pid:
                        matchups[opp_cmd]["w"] += 1
                    else:
                        matchups[opp_cmd]["l"] += 1

            match_w += pw; match_l += pl; match_d += pd

            rank = rank_by_id.get(pid)
            won = rank == 1
            podium = rank is not None and rank <= 3
            if won:    victoires += 1
            if podium: podiums += 1

            if name not in joueurs:
                joueurs[name] = {"w": 0, "l": 0, "d": 0, "victoires": 0, "podiums": 0}
            joueurs[name]["w"] += pw
            joueurs[name]["l"] += pl
            joueurs[name]["d"] += pd
            if won:    joueurs[name]["victoires"] += 1
            if podium: joueurs[name]["podiums"] += 1

    if tournois_joues == 0:
        return None

    total_m = match_w + match_l + match_d
    taux = f"{match_w / total_m * 100:.0f} %" if total_m else "—"

    return {
        "tournois_joues": tournois_joues,
        "victoires": victoires,
        "podiums": podiums,
        "match_w": match_w,
        "match_l": match_l,
        "match_d": match_d,
        "taux_victoire": taux,
        "derniere_date": derniere_date or "—",
        "joueurs": dict(sorted(joueurs.items(), key=lambda x: -(x[1]["w"] + x[1]["l"] + x[1]["d"]))),
        "matchups": dict(sorted(matchups.items(), key=lambda x: -(x[1]["w"] + x[1]["l"] + x[1]["d"]))),
    }


def _compute_commander_stats(commander: Commander) -> dict:
    """Retourne les stats par format : {'multi': ..., 'duel': ...}."""
    raw = [t for t in TournamentStorage.load() if t.get("archived", False)]

    multi = [t for t in raw if "Duel" not in t.get("format", "")]
    duel  = [t for t in raw if "Duel"     in t.get("format", "")]

    return {
        "multi": _stats_for_tournaments(commander.name, multi),
        "duel":  _stats_for_tournaments(commander.name, duel),
    }


# ---------------------------------------------------------------------------
# Image header widget
# ---------------------------------------------------------------------------

class _CommanderHeader(QFrame):
    """Bandeau image + nom + couleurs en haut du dialog."""

    HEIGHT = 160

    def __init__(self, commander: Commander, parent=None):
        super().__init__(parent)
        self._commander = commander
        self._pixmap: QPixmap | None = None
        self.setFixedHeight(self.HEIGHT)
        self.setAttribute(Qt.WA_StyledBackground, False)

        if commander.image_path:
            path = DATA_DIR / commander.image_path
            if path.exists():
                px = QPixmap(str(path))
                if not px.isNull():
                    self._pixmap = px

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        rect = QRectF(self.rect())

        # Clip arrondi
        clip = QPainterPath()
        clip.addRoundedRect(rect, 12, 12)
        painter.setClipPath(clip)

        # Fond dégradé couleurs MTG
        colors = [c for c in MTG_COLORS if c in self._commander.colors]
        grad = QLinearGradient(rect.topLeft(), rect.bottomRight())
        if not colors:
            grad.setColorAt(0, QColor("#2a2a2a"))
            grad.setColorAt(1, QColor("#111111"))
        elif len(colors) == 1:
            base = QColor(COLOR_HEX[colors[0]])
            grad.setColorAt(0, base.lighter(120))
            grad.setColorAt(1, base.darker(200))
        else:
            step = 1.0 / (len(colors) - 1)
            for i, code in enumerate(colors):
                grad.setColorAt(i * step, QColor(COLOR_HEX[code]).darker(130))
        painter.setBrush(QBrush(grad))
        painter.setPen(Qt.NoPen)
        painter.drawRect(rect)

        # Image centrée
        if self._pixmap:
            scaled = self._pixmap.scaled(
                int(rect.width()), int(rect.height()),
                Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation,
            )
            sx = (scaled.width() - int(rect.width())) // 2
            sy = max(0, (scaled.height() - int(rect.height())) // 5)
            painter.setOpacity(0.55)
            painter.drawPixmap(0, 0, scaled, sx, sy, int(rect.width()), int(rect.height()))
            painter.setOpacity(1.0)

        # Overlay sombre en bas pour le texte
        overlay = QLinearGradient(0, rect.height() * 0.35, 0, rect.height())
        overlay.setColorAt(0, QColor(0, 0, 0, 0))
        overlay.setColorAt(1, QColor(0, 0, 0, 210))
        painter.setBrush(QBrush(overlay))
        painter.setPen(Qt.NoPen)
        painter.drawRect(rect)

        # Nom
        font = QFont()
        font.setPixelSize(20)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#ffffff"))
        name_rect = QRectF(12, rect.height() - 62, rect.width() - 24, 32)
        painter.drawText(name_rect, Qt.AlignBottom | Qt.AlignLeft | Qt.TextWordWrap,
                         self._commander.name)

        # Cercles couleurs
        d, sp = 22.0, 6.0
        n = len(colors)
        x = 14.0
        cy = rect.height() - 14.0
        r2 = d / 2.0
        font2 = QFont()
        font2.setPixelSize(12)
        painter.setFont(font2)
        for code in colors:
            circle = QRectF(x, cy - r2, d, d)
            painter.setBrush(QBrush(QColor(COLOR_HEX[code])))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(circle)
            if code != "W":
                painter.setBrush(QBrush(QColor(0, 0, 0, 90)))
                painter.drawEllipse(circle)
            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor("#b8960a") if code == "W" else QColor(255, 255, 255, 200), 1.5))
            painter.drawEllipse(circle.adjusted(1, 1, -1, -1))
            painter.setPen(QColor("#2a1500") if code == "W" else QColor("#ffffff"))
            painter.drawText(circle, Qt.AlignCenter, COLOR_SYMBOLS[code])
            x += d + sp

        painter.end()


# ---------------------------------------------------------------------------
# Matchup cards
# ---------------------------------------------------------------------------

class _CommanderMatchupCard(QFrame):
    """Carte de matchup : image du commandant adverse en fond + stats W/L/D."""

    CARD_W = 165
    CARD_H = 245

    def __init__(self, opp_name: str, img_path: str | None,
                 wins: int, losses: int, draws: int, parent=None):
        super().__init__(parent)
        self._opp_name = opp_name
        self._wins   = wins
        self._losses = losses
        self._draws  = draws
        total = wins + losses + draws
        self._rate: float | None = wins / total if total else None
        self._pixmap: QPixmap | None = None
        self._hovered = False

        self.setFixedSize(self.CARD_W, self.CARD_H)
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setObjectName("MatchupCard")
        self.setCursor(Qt.PointingHandCursor)

        if img_path:
            px = QPixmap(str(DATA_DIR / img_path))
            if not px.isNull():
                self._pixmap = px

    def enterEvent(self, event):
        self._hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hovered = False
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        CW = self.CARD_W
        CH = self.CARD_H
        rect = QRectF(0, 0, CW, CH)

        STATS_H = 70          # hauteur de la zone stats en bas
        IMG_H   = CH - STATS_H  # hauteur de la zone image

        # ── Clip arrondi global ──────────────────────────────────────────
        clip = QPainterPath()
        clip.addRoundedRect(rect, 12, 12)
        painter.setClipPath(clip)

        # ── Fond sombre de base ──────────────────────────────────────────
        painter.fillRect(rect.toRect(), QColor(0x07, 0x14, 0x0e))

        # ── Image commandant ─────────────────────────────────────────────
        if self._pixmap:
            scaled = self._pixmap.scaled(
                CW, IMG_H + 20,
                Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation,
            )
            sx = (scaled.width() - CW) // 2
            painter.setOpacity(0.93 if self._hovered else 0.85)
            painter.drawPixmap(
                QRect(0, 0, CW, IMG_H),
                scaled,
                QRect(sx, 0, CW, IMG_H),
            )
            painter.setOpacity(1.0)

        # ── Gradient bas de l'image (lisibilité du nom) ──────────────────
        grad_img = QLinearGradient(0, IMG_H * 0.35, 0, IMG_H)
        grad_img.setColorAt(0, QColor(0, 0, 0, 0))
        grad_img.setColorAt(1, QColor(0x07, 0x14, 0x0e, 255))
        painter.fillRect(QRectF(0, 0, CW, IMG_H), QBrush(grad_img))

        # ── Zone stats ───────────────────────────────────────────────────
        painter.fillRect(QRectF(0, IMG_H, CW, STATS_H), QColor(0x04, 0x0d, 0x08))

        # Ligne de séparation
        painter.setPen(QPen(QColor(0x2f, 0x6f, 0x55, 100), 1))
        painter.drawLine(8, IMG_H, CW - 8, IMG_H)

        # ── Nom du commandant ────────────────────────────────────────────
        font_name = QFont()
        font_name.setPixelSize(12)
        font_name.setBold(True)
        painter.setFont(font_name)
        painter.setPen(QColor("#e8e8e8"))
        name_rect = QRectF(6, IMG_H - 40, CW - 12, 38)
        painter.drawText(
            name_rect,
            Qt.AlignBottom | Qt.AlignHCenter | Qt.TextWordWrap,
            self._opp_name,
        )

        # ── W / L / D ────────────────────────────────────────────────────
        col_w   = CW // 3
        stats_y = IMG_H + 6

        for i, (val, key, hex_col) in enumerate([
            (self._wins,   "W", "#3fd27d"),
            (self._losses, "L", "#ef4444"),
            (self._draws,  "D", "#aaaaaa"),
        ]):
            x = i * col_w
            c = QColor(hex_col)

            font_val = QFont()
            font_val.setPixelSize(17)
            font_val.setBold(True)
            painter.setFont(font_val)
            painter.setPen(c)
            painter.drawText(QRectF(x, stats_y, col_w, 22), Qt.AlignCenter, str(val))

            font_key = QFont()
            font_key.setPixelSize(9)
            painter.setFont(font_key)
            painter.setPen(c.darker(140))
            painter.drawText(QRectF(x, stats_y + 21, col_w, 13), Qt.AlignCenter, key)

        # ── Barre winrate ─────────────────────────────────────────────────
        if self._rate is not None:
            rate = self._rate
            if rate >= 0.55:
                bar_color = QColor("#3fd27d")
            elif rate >= 0.40:
                bar_color = QColor("#e8880a")
            else:
                bar_color = QColor("#ef4444")

            pct_y = stats_y + 34
            bar_x = 10
            bar_y = pct_y + 14
            bar_w = CW - 20
            bar_h = 6

            # Pourcentage
            font_pct = QFont()
            font_pct.setPixelSize(10)
            font_pct.setBold(True)
            painter.setFont(font_pct)
            painter.setPen(bar_color)
            painter.drawText(
                QRectF(bar_x, pct_y, bar_w, 14),
                Qt.AlignCenter,
                f"{rate * 100:.0f}%",
            )

            # Track
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#1a3d2e")))
            painter.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 3, 3)

            # Fill
            fill = bar_w * rate
            if fill > 0:
                painter.setBrush(QBrush(bar_color))
                painter.drawRoundedRect(QRectF(bar_x, bar_y, fill, bar_h), 3, 3)

        # ── Bordure ──────────────────────────────────────────────────────
        painter.setClipping(False)
        border = QColor(0x4f, 0x9f, 0x80) if self._hovered else QColor(0x2f, 0x6f, 0x55, 180)
        painter.setPen(QPen(border, 1.5 if self._hovered else 1.0))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect.adjusted(0.75, 0.75, -0.75, -0.75), 12, 12)

        painter.end()


class MatchupDialog(QDialog):
    """Fenêtre de matchups : grille de cartes par commandant adverse."""

    _COLS    = 4
    _SPACING = 12

    def __init__(self, commander_name: str, matchups: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Matchups — {commander_name}")
        self.setModal(True)
        self.setFixedSize(760, 620)
        self.setObjectName("PlayerStatsDialog")

        self._commander_name = commander_name
        self._all_matchups = sorted(
            matchups.items(),
            key=lambda x: x[1]["w"] / (x[1]["w"] + x[1]["l"] + x[1]["d"])
            if (x[1]["w"] + x[1]["l"] + x[1]["d"]) > 0 else 0,
            reverse=True,
        )

        raw = CommanderStorage.load()
        self._img_map: dict[str, str | None] = {
            c["name"]: c.get("image_path") for c in raw
        }

        self._grid_layout: QGridLayout | None = None
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # ── Titre + compteur ──────────────────────────────────────────────
        top = QHBoxLayout()
        title = QLabel(f"⚔️ Matchups — {self._commander_name}")
        title.setObjectName("StatsSectionTitle")
        self._count_lbl = QLabel(f"({len(self._all_matchups)})")
        self._count_lbl.setObjectName("CountLabel")
        top.addWidget(title)
        top.addWidget(self._count_lbl)
        top.addStretch()
        layout.addLayout(top)

        if not self._all_matchups:
            empty = QLabel("Aucune confrontation enregistrée.")
            empty.setObjectName("StatsLabel")
            empty.setAlignment(Qt.AlignCenter)
            layout.addWidget(empty)
            layout.addStretch()
        else:
            # ── Barre de recherche ────────────────────────────────────────
            search = QLineEdit()
            search.setObjectName("PlayersSearchInput")
            search.setPlaceholderText("🔍 Rechercher un commandant…")
            search.setClearButtonEnabled(True)
            search.textChanged.connect(self._on_search)
            layout.addWidget(search)

            # ── Scroll area + grille de cartes ────────────────────────────
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setObjectName("MatchupScroll")

            container = QWidget()
            container.setObjectName("MatchupContainer")
            self._grid_layout = QGridLayout(container)
            self._grid_layout.setContentsMargins(0, 4, 0, 12)
            self._grid_layout.setSpacing(self._SPACING)
            self._grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

            scroll.setWidget(container)
            layout.addWidget(scroll, 1)

            self._populate_grid(self._all_matchups)

        close_btn = QPushButton("Fermer")
        close_btn.setObjectName("CancelButton")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)

    def _populate_grid(self, matchups: list):
        """Vide et remplit la grille de cartes."""
        if self._grid_layout is None:
            return
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        for i, (opp_name, data) in enumerate(matchups):
            img  = self._img_map.get(opp_name)
            card = _CommanderMatchupCard(
                opp_name, img, data["w"], data["l"], data["d"]
            )
            self._grid_layout.addWidget(card, i // self._COLS, i % self._COLS)

    def _on_search(self, text: str):
        q = text.strip().lower()
        filtered = (
            [(n, d) for n, d in self._all_matchups if q in n.lower()]
            if q else self._all_matchups
        )
        total = len(self._all_matchups)
        shown = len(filtered)
        self._count_lbl.setText(f"({shown}/{total})" if q else f"({total})")
        self._populate_grid(filtered)


# ---------------------------------------------------------------------------
# Main dialog
# ---------------------------------------------------------------------------

class CommanderStatsDialog(QDialog):
    """Affiche les statistiques d'un commandant."""

    def __init__(self, commander: Commander, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Statistiques — {commander.name}")
        self.setModal(True)
        self.setFixedSize(460, 760)
        self.setObjectName("PlayerStatsDialog")

        self._commander = commander
        self._stats = _compute_commander_stats(commander)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(20, 20, 20, 20)

        # Header image
        layout.addWidget(_CommanderHeader(self._commander))

        # Onglets Duel / Multi
        tabs = QTabWidget()
        tabs.setObjectName("StatsTabWidget")

        duel_idx = None
        for fmt_key, tab_label in [("duel", "⚔️ Duel"), ("multi", "👑 Multi")]:
            s = self._stats[fmt_key]
            page = self._build_tab_page(s, is_duel=(fmt_key == "duel"))
            idx = tabs.addTab(page, tab_label)
            if fmt_key == "duel":
                duel_idx = idx

        # Onglet Duel par défaut
        if duel_idx is not None:
            tabs.setCurrentIndex(duel_idx)

        layout.addWidget(tabs, 1)

        close_btn = QPushButton("Fermer")
        close_btn.setObjectName("CancelButton")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignRight)

    def _build_tab_page(self, s: dict | None, is_duel: bool = False) -> QWidget:
        """Construit le contenu d'un onglet pour un format donné."""
        page = QWidget()
        pl = QVBoxLayout(page)
        pl.setContentsMargins(0, 8, 0, 0)
        pl.setSpacing(14)

        if s is None:
            empty = QLabel("Aucune donnée pour ce format.")
            empty.setObjectName("StatsLabel")
            empty.setAlignment(Qt.AlignCenter)
            pl.addWidget(empty)
            pl.addStretch()
            return page

        # Bouton Matchup (Duel uniquement)
        if is_duel:
            matchup_btn = QPushButton("⚔️ Voir les Matchups")
            matchup_btn.setObjectName("MatchupButton")
            matchup_btn.setCursor(Qt.PointingHandCursor)
            matchups = s.get("matchups", {})
            matchup_btn.clicked.connect(
                lambda: MatchupDialog(self._commander.name, matchups, self).exec()
            )
            pl.addWidget(matchup_btn, alignment=Qt.AlignRight)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(0, 0, 4, 0)
        cl.setSpacing(14)
        cl.addWidget(self._build_podiums(s))
        cl.addWidget(self._build_stats_grid(s))
        if s["joueurs"]:
            cl.addWidget(self._build_players_section(s))
        cl.addStretch()

        scroll.setWidget(content)
        pl.addWidget(scroll)
        return page

    # ------------------------------------------------------------------

    def _make_stat_card(self, emoji: str, label: str, value: str) -> QFrame:
        card = QFrame()
        card.setObjectName("PodiumCard")
        cl = QVBoxLayout(card)
        cl.setSpacing(4)
        cl.setAlignment(Qt.AlignCenter)
        e = QLabel(emoji)
        e.setObjectName("PodiumEmoji")
        e.setAlignment(Qt.AlignCenter)
        v = QLabel(value)
        v.setObjectName("PodiumCount")
        v.setAlignment(Qt.AlignCenter)
        l = QLabel(label)
        l.setObjectName("PodiumLabel")
        l.setAlignment(Qt.AlignCenter)
        cl.addWidget(e)
        cl.addWidget(v)
        cl.addWidget(l)
        return card

    def _build_podiums(self, s: dict) -> QFrame:
        frame = QFrame()
        frame.setObjectName("StatsSection")
        layout = QVBoxLayout(frame)
        layout.setSpacing(12)

        title = QLabel("Palmarès")
        title.setObjectName("StatsSectionTitle")
        layout.addWidget(title)

        row = QHBoxLayout()
        row.setSpacing(16)
        row.addWidget(self._make_stat_card("🥇", "Victoires", str(s["victoires"])))
        row.addWidget(self._make_stat_card("🥈", "Podiums",   str(s["podiums"])))
        row.addWidget(self._make_stat_card("🎮", "Tournois",  str(s["tournois_joues"])))
        layout.addLayout(row)
        return frame

    def _build_stats_grid(self, s: dict) -> QFrame:
        frame = QFrame()
        frame.setObjectName("StatsSection")
        layout = QVBoxLayout(frame)
        layout.setSpacing(10)

        title = QLabel("Détails")
        title.setObjectName("StatsSectionTitle")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(8)

        total_m = s["match_w"] + s["match_l"] + s["match_d"]
        ratio = f"{s['match_w']} / {s['match_l']} / {s['match_d']}"
        rows = [
            ("W / L / D",            ratio),
            ("Taux de victoire",      s["taux_victoire"]),
            ("Parties jouées",        str(total_m)),
            ("Dernière utilisation",  s["derniere_date"]),
            ("Joueurs différents",    str(len(s["joueurs"]))),
        ]

        for i, (label, value) in enumerate(rows):
            lw = QLabel(label)
            lw.setObjectName("StatsLabel")
            vw = QLabel(value)
            vw.setObjectName("StatsValue")
            grid.addWidget(lw, i, 0)
            grid.addWidget(vw, i, 1)

        layout.addLayout(grid)
        return frame

    def _build_players_section(self, s: dict) -> QFrame:
        frame = QFrame()
        frame.setObjectName("StatsSection")
        layout = QVBoxLayout(frame)
        layout.setSpacing(8)

        title = QLabel("Joueurs")
        title.setObjectName("StatsSectionTitle")
        layout.addWidget(title)

        grid = QGridLayout()
        grid.setSpacing(6)
        grid.setColumnStretch(0, 1)

        for col, text in enumerate(["Nom", "W", "L", "D", "🏆"]):
            h = QLabel(text)
            h.setObjectName("StatsLabel")
            h.setAlignment(Qt.AlignCenter if col > 0 else Qt.AlignLeft)
            grid.addWidget(h, 0, col)

        for i, (name, data) in enumerate(s["joueurs"].items(), start=1):
            for col, val in enumerate([
                name,
                str(data["w"]),
                str(data["l"]),
                str(data["d"]),
                str(data["victoires"]),
            ]):
                lw = QLabel(val)
                lw.setObjectName("StatsValue")
                lw.setAlignment(Qt.AlignCenter if col > 0 else Qt.AlignLeft)
                grid.addWidget(lw, i, col)

        layout.addLayout(grid)
        return frame


# ===========================================================================
# GLOBAL STATS — stats de tous les commandants
# ===========================================================================

# ---------------------------------------------------------------------------
# Calcul
# ---------------------------------------------------------------------------

def _compute_global_stats() -> dict:
    """
    Calcule les stats globales sur tous les tournois (archivés ou non).
    Retourne :
        {
            'wins':       [(name, count, img_path), ...],  # triés par nb victoires totales
            'wins_multi': [(name, count, img_path), ...],  # triés par nb victoires Multi
            'wins_duel':  [(name, count, img_path), ...],  # triés par nb victoires Duel
            'multi':      [(name, count, img_path), ...],  # triés par nb tournois Multi joués
            'duel':       [(name, count, img_path), ...],  # triés par nb tournois Duel joués
        }
    """
    tournaments = TournamentStorage.load()
    commanders_raw = CommanderStorage.load()
    img_map: dict[str, str | None] = {c["name"]: c.get("image_path") for c in commanders_raw}

    wins:       dict[str, int] = {}
    wins_multi: dict[str, int] = {}
    wins_duel:  dict[str, int] = {}
    multi: dict[str, int] = {}
    duel:  dict[str, int] = {}

    for t in tournaments:
        is_duel = "Duel" in t.get("format", "")
        target = duel if is_duel else multi

        # Compte chaque commandant une seule fois par tournoi
        cmds_seen: set[str] = set()
        for p in t.get("players", []):
            cmd = p.get("commander", "")
            if cmd and cmd not in cmds_seen:
                cmds_seen.add(cmd)
                target[cmd] = target.get(cmd, 0) + 1

        # Victoires : rang 1 du classement final
        rank_by_id = _final_ranking(t)
        pid_to_cmd = {p["id"]: p.get("commander", "") for p in t.get("players", [])}
        wins_target = wins_duel if is_duel else wins_multi
        for pid, rank in rank_by_id.items():
            if rank == 1:
                cmd = pid_to_cmd.get(pid, "")
                if cmd:
                    wins[cmd]        = wins.get(cmd, 0) + 1
                    wins_target[cmd] = wins_target.get(cmd, 0) + 1

    def to_ranked(d: dict) -> list[tuple[str, int, str | None]]:
        return [
            (name, count, img_map.get(name))
            for name, count in sorted(d.items(), key=lambda x: -x[1])
        ]

    return {
        "wins":       to_ranked(wins),
        "wins_multi": to_ranked(wins_multi),
        "wins_duel":  to_ranked(wins_duel),
        "multi":      to_ranked(multi),
        "duel":       to_ranked(duel),
    }


# ---------------------------------------------------------------------------
# _Thumb — image circulaire miniature
# ---------------------------------------------------------------------------

class _Thumb(QFrame):
    """Image circulaire miniature d'un commandant."""

    def __init__(self, img_path: str | None, size: int = 44, parent=None):
        super().__init__(parent)
        self._size = size
        self._pixmap: QPixmap | None = None
        self.setFixedSize(size, size)
        self.setAttribute(Qt.WA_StyledBackground, False)
        if img_path:
            px = QPixmap(str(DATA_DIR / img_path))
            if not px.isNull():
                self._pixmap = px

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        s = self._size
        circle = QRectF(0, 0, s, s)

        clip = QPainterPath()
        clip.addEllipse(circle)
        painter.setClipPath(clip)

        if self._pixmap:
            scaled = self._pixmap.scaled(s, s, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            sx = (scaled.width() - s) // 2
            sy = max(0, (scaled.height() - s) // 5)
            painter.drawPixmap(QRect(0, 0, s, s), scaled, QRect(sx, sy, s, s))
        else:
            painter.fillRect(QRect(0, 0, s, s), QColor("#1a3d2e"))

        painter.setClipping(False)
        painter.setPen(QPen(QColor("#2f6f55"), 1.5))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(circle.adjusted(0.75, 0.75, -0.75, -0.75))
        painter.end()


# ---------------------------------------------------------------------------
# _PodiumCard — grande carte image pour le podium
# ---------------------------------------------------------------------------

class _PodiumCard(QFrame):
    """Carte du podium : image pleine + badge rang + nom + compteur."""

    _RANK_COLOR = {1: "#FFD700", 2: "#B0B8C1", 3: "#CD7F32"}
    _RANK_LABEL = {1: "1er", 2: "2e", 3: "3e"}
    _RANK_ICON  = {1: "🥇", 2: "🥈", 3: "🥉"}
    _SIZES      = {1: (210, 310), 2: (180, 272), 3: (162, 248)}

    def __init__(self, rank: int, name: str, value: int, suffix: str,
                 img_path: str | None, parent=None):
        super().__init__(parent)
        self._rank   = rank
        self._name   = name
        self._value  = value
        self._suffix = suffix
        self._pixmap: QPixmap | None = None
        w, h = self._SIZES.get(rank, (155, 225))
        self.setFixedSize(w, h)
        self.setAttribute(Qt.WA_StyledBackground, False)
        if img_path:
            px = QPixmap(str(DATA_DIR / img_path))
            if not px.isNull():
                self._pixmap = px

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        CW, CH = self.width(), self.height()
        rect = QRectF(0, 0, CW, CH)
        rc   = QColor(self._RANK_COLOR[self._rank])

        # Clip arrondi
        clip = QPainterPath()
        clip.addRoundedRect(rect, 14, 14)
        painter.setClipPath(clip)

        # Fond sombre
        painter.fillRect(rect.toRect(), QColor(0x07, 0x14, 0x0e))

        # Image pleine
        if self._pixmap:
            scaled = self._pixmap.scaled(CW, CH, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            sx = (scaled.width() - CW) // 2
            sy = max(0, (scaled.height() - CH) // 5)
            painter.setOpacity(0.88)
            painter.drawPixmap(QRect(0, 0, CW, CH), scaled, QRect(sx, sy, CW, CH))
            painter.setOpacity(1.0)

        # Gradient bas (lisibilité texte)
        grad = QLinearGradient(0, CH * 0.32, 0, CH)
        grad.setColorAt(0, QColor(0, 0, 0, 0))
        grad.setColorAt(1, QColor(0, 0, 0, 240))
        painter.fillRect(rect, QBrush(grad))

        # Badge rang (coin haut droit)
        br = 18
        badge = QRectF(CW - br * 2 - 7, 7, br * 2, br * 2)
        painter.setBrush(QBrush(rc))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(badge)
        fb = QFont(); fb.setPixelSize(12); fb.setBold(True)
        painter.setFont(fb)
        painter.setPen(QColor("#000000"))
        painter.drawText(badge, Qt.AlignCenter, self._RANK_LABEL[self._rank])

        # Nom du commandant
        fn = QFont(); fn.setPixelSize(12); fn.setBold(True)
        painter.setFont(fn)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(
            QRectF(6, CH - 56, CW - 12, 30),
            Qt.AlignBottom | Qt.AlignHCenter | Qt.TextWordWrap,
            self._name,
        )

        # Valeur (victoires / parties)
        fv = QFont(); fv.setPixelSize(16); fv.setBold(True)
        painter.setFont(fv)
        painter.setPen(rc)
        painter.drawText(
            QRectF(6, CH - 27, CW - 12, 23),
            Qt.AlignCenter,
            f"{self._RANK_ICON[self._rank]} {self._value} {self._suffix}",
        )

        # Bordure colorée selon le rang
        painter.setClipping(False)
        painter.setPen(QPen(rc.darker(130), 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 14, 14)

        painter.end()


# ---------------------------------------------------------------------------
# _RankingRow — ligne de classement avec image circulaire
# ---------------------------------------------------------------------------

class _RankingRow(QFrame):
    """Ligne de classement : rang + image circulaire + nom + compteur."""

    _RANK_COLOR = {1: "#FFD700", 2: "#B0B8C1", 3: "#CD7F32"}

    def __init__(self, rank: int, name: str, count: int, suffix: str,
                 img_path: str | None, parent=None):
        super().__init__(parent)
        self.setObjectName("RankingRow")
        self.setFixedHeight(58)

        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 4, 14, 4)
        lay.setSpacing(10)

        # Numéro de rang (coloré pour le top 3)
        rk_lbl = QLabel(f"#{rank}")
        color = self._RANK_COLOR.get(rank, "")
        if color:
            rk_lbl.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 14px;")
        else:
            rk_lbl.setObjectName("RankingNumber")
        rk_lbl.setFixedWidth(34)
        rk_lbl.setAlignment(Qt.AlignCenter)
        lay.addWidget(rk_lbl)

        # Image circulaire
        lay.addWidget(_Thumb(img_path, size=46))

        # Nom
        name_lbl = QLabel(name)
        name_lbl.setObjectName("StatsLabel")
        lay.addWidget(name_lbl, 1)

        # Compteur (en gras)
        val_lbl = QLabel(f"<b>{count}</b> {suffix}")
        val_lbl.setObjectName("StatsValue")
        val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay.addWidget(val_lbl)


# ---------------------------------------------------------------------------
# Helpers de construction d'UI
# ---------------------------------------------------------------------------

def _make_podium_row(data: list, suffix: str) -> QHBoxLayout:
    """
    Construit le podium visuel : 2e (gauche), 1er (centre), 3e (droite).
    Les cartes sont alignées en bas pour simuler les marches d'un podium.
    """
    row = QHBoxLayout()
    row.setAlignment(Qt.AlignCenter | Qt.AlignBottom)
    row.setSpacing(16)

    order = [
        (2, data[1] if len(data) > 1 else None),
        (1, data[0]),
        (3, data[2] if len(data) > 2 else None),
    ]

    for rank, entry in order:
        if entry is None:
            row.addStretch()
            continue
        name, count, img = entry
        card = _PodiumCard(rank, name, count, suffix, img)
        # Wrapper avec stretch en haut → pousse la carte vers le bas (effet marches)
        wrapper = QWidget()
        wl = QVBoxLayout(wrapper)
        wl.setContentsMargins(0, 0, 0, 0)
        wl.setSpacing(0)
        wl.addStretch()
        wl.addWidget(card)
        row.addWidget(wrapper)

    return row


def _make_ranking_scroll(data: list, suffix: str) -> QScrollArea:
    """Construit la liste scrollable du classement complet avec images (pour les dialogs)."""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    scroll.setFrameShape(QFrame.NoFrame)
    scroll.setObjectName("GlobalStatsScroll")

    container = QWidget()
    container.setObjectName("GlobalStatsContainer")
    cl = QVBoxLayout(container)
    cl.setContentsMargins(0, 0, 0, 8)
    cl.setSpacing(4)
    for rank, (name, count, img) in enumerate(data, 1):
        cl.addWidget(_RankingRow(rank, name, count, suffix, img))
    cl.addStretch()

    scroll.setWidget(container)
    return scroll


def _make_ranking_list(data: list, suffix: str) -> QWidget:
    """Construit la liste plate du classement complet (pour les vues avec scroll externe)."""
    container = QWidget()
    container.setObjectName("GlobalStatsContainer")
    cl = QVBoxLayout(container)
    cl.setContentsMargins(0, 0, 0, 0)
    cl.setSpacing(4)
    for rank, (name, count, img) in enumerate(data, 1):
        cl.addWidget(_RankingRow(rank, name, count, suffix, img))
    return container


# ---------------------------------------------------------------------------
# CommanderGlobalStatsDialog
# ---------------------------------------------------------------------------

class CommanderGlobalStatsDialog(QDialog):
    """
    Statistiques globales des commandants sur tous les tournois.

    Trois onglets :
    - 🏆 Victoires : podium + classement par nb de victoires
    - 👑 Multi     : podium + commandants les plus joués en Multi
    - ⚔️  Duel     : podium + commandants les plus joués en Duel
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🏆 Stats globales — Commandants")
        self.setModal(True)
        self.setFixedSize(820, 700)
        self.setObjectName("PlayerStatsDialog")
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        self._data = _compute_global_stats()
        self._build_ui()

    def _build_ui(self):
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 20, 20, 20)
        lay.setSpacing(16)

        title = QLabel("🏆 Statistiques globales des Commandants")
        title.setObjectName("SectionTitle")
        lay.addWidget(title)

        tabs = QTabWidget()
        tabs.setObjectName("StatsTabWidget")
        tabs.addTab(
            self._build_tab(self._data["wins"],  "victoire(s)", "Aucune victoire enregistrée."),
            "🏆 Victoires",
        )
        tabs.addTab(
            self._build_tab(self._data["multi"], "partie(s)", "Aucun tournoi Multi enregistré."),
            "👑 Multi",
        )
        tabs.addTab(
            self._build_tab(self._data["duel"],  "partie(s)", "Aucun tournoi Duel enregistré."),
            "⚔️ Duel",
        )
        lay.addWidget(tabs, 1)

        close_btn = QPushButton("Fermer")
        close_btn.setObjectName("CancelButton")
        close_btn.clicked.connect(self.accept)
        lay.addWidget(close_btn, alignment=Qt.AlignRight)

    def _build_tab(self, data: list, suffix: str, empty_msg: str) -> QWidget:
        """
        Onglet :
        - Podium visuel en haut (top 3 avec grandes images)
        - Classement complet scrollable en bas (si plus de 3 entrées)
        """
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.setSpacing(12)

        if not data:
            lbl = QLabel(empty_msg)
            lbl.setObjectName("StatsLabel")
            lbl.setAlignment(Qt.AlignCenter)
            lay.addWidget(lbl)
            lay.addStretch()
            return page

        # Podium (top 3)
        lay.addLayout(_make_podium_row(data, suffix))

        # Classement complet si plus de 3 entrées
        if len(data) > 3:
            sep = QLabel("Classement complet")
            sep.setObjectName("StatsSectionTitle")
            lay.addWidget(sep)
            lay.addWidget(_make_ranking_scroll(data, suffix), 1)

        return page
