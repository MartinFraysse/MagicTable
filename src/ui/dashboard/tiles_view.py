from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame, QSizePolicy


class DashboardTilesView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tile_active = self._tile("🔴", "Tournoi", "Inactif")
        self.tile_name = self._tile("🏷", "Nom", "-")
        self.tile_players = self._tile("👥", "Joueurs", "-")
        self.tile_tables = self._tile("🪑", "Tables", "-")
        self.tile_round = self._tile("🌀", "Round", "-")
        self.tile_timer = self._tile("⏱", "Prochaine round", "50:00")

        for tile in (
            self.tile_active,
            self.tile_name,
            self.tile_players,
            self.tile_tables,
            self.tile_round,
            self.tile_timer,
        ):
            layout.addWidget(tile)

    def _tile(self, icon, title, value):
        frame = QFrame()
        frame.setObjectName("DashboardTile")
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        frame.setMinimumWidth(100)

        layout = QVBoxLayout(frame)
        layout.setSpacing(4)
        layout.setContentsMargins(12, 12, 12, 12)

        # === ACCENT VISUEL ===
        accent = QFrame()
        accent.setObjectName("DashboardTileAccent")
        accent.setFixedWidth(4)
        layout.insertWidget(0, accent)

        # === ICON ===
        lbl_icon = QLabel(icon)
        lbl_icon.setObjectName("DashboardTileIcon")

        # === VALUE ===
        lbl_value = QLabel(value)
        lbl_value.setObjectName("DashboardTileValue")

        # === TITLE ===
        lbl_title = QLabel(title)
        lbl_title.setObjectName("DashboardTileTitle")

        layout.addWidget(lbl_icon)
        layout.addWidget(lbl_value)
        layout.addWidget(lbl_title)

        # 🔑 SAUVEGARDE DES RÉFÉRENCES
        frame.icon_label = lbl_icon
        frame.value_label = lbl_value

        return frame


    def set_timer_text(self, value: str):
        self.tile_timer.value_label.setText(value)

    def update_for_tournament(
        self,
        *,
        name: str,
        round_number: int,
        max_rounds: int,
        player_count: int,
        table_count: int,
    ):
        self.set_active()
        self.tile_name.value_label.setText(name)
        self.tile_round.value_label.setText(f"#{round_number}/{max_rounds}")
        self.tile_players.value_label.setText(str(player_count))
        self.tile_tables.value_label.setText(str(table_count))

    def set_active(self):
        self.tile_active.value_label.setText("Active")
        self.tile_active.icon_label.setText("🟢")

    def reset(self):
        """Réinitialise les tiles à leur état initial."""
        self.tile_active.value_label.setText("Inactif")
        self.tile_active.icon_label.setText("🔴")
        self.tile_name.value_label.setText("-")
        self.tile_players.value_label.setText("-")
        self.tile_tables.value_label.setText("-")
        self.tile_round.value_label.setText("-")
        self.tile_timer.value_label.setText("--:--")
