from PySide6.QtCore import Qt, QRectF, QRect
from PySide6.QtGui import (
    QPainter, QPixmap, QLinearGradient, QBrush, QColor,
    QPainterPath, QFont, QPen,
)
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QGridLayout,
    QScrollArea, QWidget, QTabWidget, QLineEdit
)

from core.commander import Commander, MTG_COLORS, COLOR_HEX, COLOR_SYMBOLS
from core.commander_stats import compute_commander_stats
from storage.base import DATA_DIR
from storage.commanders import CommanderStorage
from storage.tournaments import TournamentStorage


def _compute_commander_stats(commander: Commander) -> dict:
    """Retourne les stats par format : {'multi': ..., 'duel': ...}."""
    return compute_commander_stats(commander.name, TournamentStorage.load())


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
