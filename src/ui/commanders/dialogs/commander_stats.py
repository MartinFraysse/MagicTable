from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import (
    QPainter, QPixmap, QLinearGradient, QBrush, QColor,
    QPainterPath, QFont, QPen,
)
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QScrollArea, QWidget, QTabWidget,
)

from core.commander import Commander, MTG_COLORS, COLOR_HEX, COLOR_SYMBOLS
from storage.base import DATA_DIR
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

            for m in bracket_matches:
                if not m.get("finished") or pid not in (m.get("player1_id"), m.get("player2_id")):
                    continue
                if m.get("winner_id") == pid: pw += 1
                else:                          pl += 1

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
# Main dialog
# ---------------------------------------------------------------------------

class CommanderStatsDialog(QDialog):
    """Affiche les statistiques d'un commandant."""

    def __init__(self, commander: Commander, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Statistiques — {commander.name}")
        self.setModal(True)
        self.setMinimumSize(460, 540)
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
            page = self._build_tab_page(s)
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

    def _build_tab_page(self, s: dict | None) -> QWidget:
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
