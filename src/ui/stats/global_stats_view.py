"""Vue des statistiques globales."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QScrollArea, QFrame, QProgressBar,
)
from PySide6.QtCore import Qt, QRectF, QRect
from PySide6.QtGui import (
    QPainter, QPixmap, QLinearGradient, QBrush, QColor,
    QPainterPath, QFont,
)

from core.stats_analyzer import StatsAnalyzer
from ui.commanders.dialogs.commander_stats import _compute_global_stats, _RankingRow
from storage.base import DATA_DIR


# ---------------------------------------------------------------------------
# _VictoryTile — carte image pleine pour le commandant le plus victorieux
# ---------------------------------------------------------------------------

class _VictoryTile(QFrame):
    """Carte à image de fond : commandant le plus victorieux d'un format."""

    W, H = 220, 160

    def __init__(self, format_label: str, parent=None):
        super().__init__(parent)
        self._format_label = format_label
        self._name: str = ""
        self._count: int = 0
        self._pixmap: QPixmap | None = None
        self.setFixedSize(self.W, self.H)
        self.setAttribute(Qt.WA_StyledBackground, False)

    def set_data(self, name: str, count: int, img_path: str | None):
        self._name = name
        self._count = count
        self._pixmap = None
        if img_path:
            px = QPixmap(str(DATA_DIR / img_path))
            if not px.isNull():
                self._pixmap = px
        self.update()

    def clear_data(self):
        self._name = ""
        self._count = 0
        self._pixmap = None
        self.update()

    def paintEvent(self, _event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        W, H = self.W, self.H
        rect = QRectF(0, 0, W, H)

        # Clip arrondi
        clip = QPainterPath()
        clip.addRoundedRect(rect, 12, 12)
        painter.setClipPath(clip)

        # Fond sombre de base
        painter.fillRect(rect.toRect(), QColor(0x07, 0x14, 0x0e))

        # Image de fond pleine
        if self._pixmap:
            scaled = self._pixmap.scaled(W, H, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            sx = (scaled.width() - W) // 2
            sy = max(0, (scaled.height() - H) // 5)
            painter.setOpacity(0.78)
            painter.drawPixmap(QRect(0, 0, W, H), scaled, QRect(sx, sy, W, H))
            painter.setOpacity(1.0)

        # Gradient sombre sur le bas (lisibilité texte)
        grad = QLinearGradient(0, H * 0.22, 0, H)
        grad.setColorAt(0, QColor(0, 0, 0, 0))
        grad.setColorAt(1, QColor(0, 0, 0, 235))
        painter.fillRect(rect, QBrush(grad))

        # Badge format (coin haut gauche)
        fbadge = QFont()
        fbadge.setPixelSize(11)
        fbadge.setBold(True)
        painter.setFont(fbadge)
        fm = painter.fontMetrics()
        bw = fm.horizontalAdvance(self._format_label) + 16
        badge_rect = QRectF(8, 8, bw, 22)
        painter.setBrush(QBrush(QColor(0, 0, 0, 170)))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(badge_rect, 6, 6)
        painter.setPen(QColor("#3ad68a"))
        painter.drawText(badge_rect, Qt.AlignCenter, self._format_label)

        if not self._name:
            painter.setPen(QColor("#4a7a68"))
            fn = QFont()
            fn.setPixelSize(12)
            painter.setFont(fn)
            painter.drawText(rect, Qt.AlignCenter, "Aucune donnée")
            painter.end()
            return

        # Nom du commandant — bas gauche, petit
        fn = QFont()
        fn.setPixelSize(12)
        painter.setFont(fn)
        painter.setPen(QColor("#c8f0dc"))
        painter.drawText(
            QRectF(10, H - 54, W * 0.58, 40),
            Qt.AlignLeft | Qt.AlignBottom | Qt.TextWordWrap,
            self._name,
        )

        # Nombre de victoires — bas droite, gros, doré
        fv = QFont()
        fv.setPixelSize(34)
        fv.setBold(True)
        painter.setFont(fv)
        painter.setPen(QColor("#FFD700"))
        painter.drawText(
            QRectF(W * 0.55, H - 62, W * 0.42, 50),
            Qt.AlignRight | Qt.AlignBottom,
            str(self._count),
        )

        # Sous-label "tournoi(s) remporté(s)"
        fs = QFont()
        fs.setPixelSize(9)
        painter.setFont(fs)
        painter.setPen(QColor("#8aaa98"))
        suffix_s = "s" if self._count > 1 else ""
        painter.drawText(
            QRectF(W * 0.45, H - 14, W * 0.52, 12),
            Qt.AlignRight | Qt.AlignVCenter,
            f"tournoi{suffix_s} remporté{suffix_s}",
        )

        painter.end()


# ---------------------------------------------------------------------------
# GlobalStatsView
# ---------------------------------------------------------------------------

class GlobalStatsView(QWidget):
    """Vue affichant les statistiques globales des tournois."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("GlobalStatsView")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        content = QWidget()
        content.setAttribute(Qt.WA_StyledBackground, True)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(24)

        # ── KPI ──────────────────────────────────────────────────────────────
        title = QLabel("Vue d'ensemble")
        title.setObjectName("StatsSectionTitle")
        content_layout.addWidget(title)

        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(16)
        self.tile_tournaments = self._make_kpi_tile("0", "Tournois joués")
        self.tile_players     = self._make_kpi_tile("0", "Joueurs uniques")
        self.tile_tables      = self._make_kpi_tile("0", "Tables jouées")
        kpi_row.addWidget(self.tile_tournaments)
        kpi_row.addWidget(self.tile_players)
        kpi_row.addWidget(self.tile_tables)
        kpi_row.addStretch()
        content_layout.addLayout(kpi_row)

        # ── Distribution formats ──────────────────────────────────────────────
        fmt_title = QLabel("Distribution des formats")
        fmt_title.setObjectName("StatsSectionTitle")
        content_layout.addWidget(fmt_title)

        self.format_container = QWidget()
        self.format_container.setObjectName("ChartContainer")
        self.format_layout = QVBoxLayout(self.format_container)
        self.format_layout.setContentsMargins(16, 16, 16, 16)
        self.format_layout.setSpacing(12)
        content_layout.addWidget(self.format_container)

        # ── Commandants les plus victorieux (tuiles image) ────────────────────
        vic_title = QLabel("Commandants les plus victorieux")
        vic_title.setObjectName("StatsSectionTitle")
        content_layout.addWidget(vic_title)

        vic_row = QHBoxLayout()
        vic_row.setSpacing(16)
        self._vic_multi = _VictoryTile("Multi")
        self._vic_duel  = _VictoryTile("Duel")
        vic_row.addWidget(self._vic_multi)
        vic_row.addWidget(self._vic_duel)
        vic_row.addStretch()
        content_layout.addLayout(vic_row)

        # ── Commandants les plus joués (listes) ───────────────────────────────
        played_title = QLabel("Commandants les plus joués")
        played_title.setObjectName("StatsSectionTitle")
        content_layout.addWidget(played_title)

        played_row = QHBoxLayout()
        played_row.setSpacing(24)

        self._played_multi_col = QWidget()
        self._played_multi_col.setAttribute(Qt.WA_StyledBackground, True)
        self._played_multi_layout = QVBoxLayout(self._played_multi_col)
        self._played_multi_layout.setContentsMargins(0, 0, 0, 0)
        self._played_multi_layout.setSpacing(4)

        self._played_duel_col = QWidget()
        self._played_duel_col.setAttribute(Qt.WA_StyledBackground, True)
        self._played_duel_layout = QVBoxLayout(self._played_duel_col)
        self._played_duel_layout.setContentsMargins(0, 0, 0, 0)
        self._played_duel_layout.setSpacing(4)

        played_row.addWidget(self._played_multi_col, 1)
        played_row.addWidget(self._played_duel_col, 1)
        content_layout.addLayout(played_row)

        content_layout.addStretch()

        scroll.setWidget(content)
        layout.addWidget(scroll)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _make_kpi_tile(self, value: str, label: str) -> QFrame:
        tile = QFrame()
        tile.setObjectName("StatsTile")
        tile.setAttribute(Qt.WA_StyledBackground, True)

        lay = QVBoxLayout(tile)
        lay.setContentsMargins(16, 16, 16, 16)
        lay.setSpacing(4)

        value_lbl = QLabel(value)
        value_lbl.setObjectName("StatsTileValue")
        value_lbl.setAlignment(Qt.AlignCenter)

        text_lbl = QLabel(label)
        text_lbl.setObjectName("StatsTileLabel")
        text_lbl.setAlignment(Qt.AlignCenter)

        lay.addWidget(value_lbl)
        lay.addWidget(text_lbl)
        tile.value_label = value_lbl
        return tile

    def _make_played_col_header(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setObjectName("StatsSectionTitle")
        return lbl

    # ── Update ────────────────────────────────────────────────────────────────

    def update_stats(self, analyzer: StatsAnalyzer):
        global_stats = analyzer.get_global_stats()
        self.tile_tournaments.value_label.setText(str(global_stats["total_tournaments"]))
        self.tile_players.value_label.setText(str(global_stats["total_unique_players"]))
        self.tile_tables.value_label.setText(str(global_stats["total_tables"]))

        self._update_format_distribution(analyzer.get_format_distribution())

        data = _compute_global_stats()
        self._update_victory_tiles(data)
        self._update_played_lists(data)

    def _update_format_distribution(self, distribution: dict[str, int]):
        while self.format_layout.count():
            item = self.format_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not distribution:
            lbl = QLabel("Aucun tournoi archivé")
            lbl.setObjectName("EmptyState")
            lbl.setAlignment(Qt.AlignCenter)
            self.format_layout.addWidget(lbl)
            return

        total = sum(distribution.values())
        for fmt, count in sorted(distribution.items(), key=lambda x: -x[1]):
            pct = count / total * 100 if total else 0

            row = QWidget()
            rl = QHBoxLayout(row)
            rl.setContentsMargins(0, 0, 0, 0)
            rl.setSpacing(12)

            name_lbl = QLabel(fmt)
            name_lbl.setStyleSheet("color: #eafff6; font-size: 14px; font-weight: 500;")
            name_lbl.setMinimumWidth(150)

            bar = QProgressBar()
            bar.setMinimum(0)
            bar.setMaximum(100)
            bar.setValue(int(pct))
            bar.setTextVisible(False)
            bar.setFixedHeight(24)
            bar.setStyleSheet("""
                QProgressBar { background-color: #1c4a3a; border-radius: 4px; border: none; }
                QProgressBar::chunk { background-color: #3ad68a; border-radius: 4px; }
            """)

            val_lbl = QLabel(f"{count} ({pct:.0f}%)")
            val_lbl.setStyleSheet("color: #b6dcd0; font-size: 13px;")
            val_lbl.setMinimumWidth(80)
            val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            rl.addWidget(name_lbl)
            rl.addWidget(bar, 1)
            rl.addWidget(val_lbl)
            self.format_layout.addWidget(row)

    def _update_victory_tiles(self, data: dict):
        wins_multi = data.get("wins_multi", [])
        wins_duel  = data.get("wins_duel",  [])

        if wins_multi:
            n, c, img = wins_multi[0]
            self._vic_multi.set_data(n, c, img)
        else:
            self._vic_multi.clear_data()

        if wins_duel:
            n, c, img = wins_duel[0]
            self._vic_duel.set_data(n, c, img)
        else:
            self._vic_duel.clear_data()

    def _update_played_lists(self, data: dict):
        for layout in (self._played_multi_layout, self._played_duel_layout):
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

        multi = data.get("multi", [])[:6]
        duel  = data.get("duel",  [])[:6]

        for layout, header, entries, suffix in [
            (self._played_multi_layout, "Multi",  multi, "tournoi"),
            (self._played_duel_layout,  "Duel",   duel,  "tournoi"),
        ]:
            lbl = QLabel(header)
            lbl.setObjectName("StatsSectionTitle")
            layout.addWidget(lbl)

            if not entries:
                empty = QLabel("Aucune donnée")
                empty.setObjectName("EmptyState")
                empty.setAlignment(Qt.AlignCenter)
                layout.addWidget(empty)
            else:
                for rank, (name, count, img) in enumerate(entries, 1):
                    s = "s" if count > 1 else ""
                    layout.addWidget(_RankingRow(rank, name, count, f"tournoi{s}", img))

        self._played_multi_layout.addStretch()
        self._played_duel_layout.addStretch()

    def clear(self):
        self.tile_tournaments.value_label.setText("0")
        self.tile_players.value_label.setText("0")
        self.tile_tables.value_label.setText("0")
        while self.format_layout.count():
            item = self.format_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
