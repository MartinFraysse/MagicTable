from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QFrame, QPushButton, QSpinBox, QMessageBox,
    QScrollArea
)
from PySide6.QtCore import Qt, Signal

from storage.tournaments import TournamentStorage
from storage.regular_players import RegularPlayerStorage


class SettingsView(QWidget):
    """Vue des paramètres de l'application."""

    # Signal émis quand la durée du timer change
    timer_duration_changed = Signal(int)
    # Signal émis quand des tournois sont supprimés depuis les paramètres
    tournaments_cleared = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("SettingsView")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Header
        title = QLabel("⚙️ Paramètres")
        title.setObjectName("SettingsTitle")
        layout.addWidget(title)

        # Scroll area pour le contenu
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setObjectName("SettingsScroll")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(20)

        # Section Timer
        timer_section = self._build_timer_section()
        content_layout.addWidget(timer_section)

        # Section Données
        data_section = self._build_data_section()
        content_layout.addWidget(data_section)

        # Section À propos
        about_section = self._build_about_section()
        content_layout.addWidget(about_section)

        content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)

    def _build_timer_section(self) -> QFrame:
        """Construit la section des paramètres du timer."""
        frame = QFrame()
        frame.setObjectName("SettingsSection")

        layout = QVBoxLayout(frame)
        layout.setSpacing(12)

        title = QLabel("Durée des rounds")
        title.setObjectName("SettingsSectionTitle")
        layout.addWidget(title)

        row = QHBoxLayout()

        label = QLabel("Durée par défaut du timer :")
        label.setObjectName("SettingsLabel")

        self.timer_spinbox = QSpinBox()
        self.timer_spinbox.setObjectName("SettingsSpinBox")
        self.timer_spinbox.setRange(1, 120)
        self.timer_spinbox.setValue(50)
        self.timer_spinbox.setSuffix(" minutes")
        self.timer_spinbox.setMinimumWidth(120)

        row.addWidget(label)
        row.addStretch()
        row.addWidget(self.timer_spinbox)

        layout.addLayout(row)

        hint = QLabel("Durée affichée pour chaque round de tournoi")
        hint.setObjectName("SettingsHint")
        layout.addWidget(hint)

        return frame

    def _build_data_section(self) -> QFrame:
        """Construit la section de gestion des données."""
        frame = QFrame()
        frame.setObjectName("SettingsSection")

        layout = QVBoxLayout(frame)
        layout.setSpacing(12)

        title = QLabel("Gestion des données")
        title.setObjectName("SettingsSectionTitle")
        layout.addWidget(title)

        # Stats actuelles
        stats_layout = QHBoxLayout()

        self.tournaments_count = QLabel("0 tournois")
        self.tournaments_count.setObjectName("SettingsStats")

        self.players_count = QLabel("0 joueurs")
        self.players_count.setObjectName("SettingsStats")

        stats_layout.addWidget(self.tournaments_count)
        stats_layout.addWidget(self.players_count)
        stats_layout.addStretch()

        layout.addLayout(stats_layout)

        # Boutons
        buttons_layout = QHBoxLayout()

        reset_archived_btn = QPushButton("Supprimer les tournois archivés")
        reset_archived_btn.setObjectName("DangerButton")
        reset_archived_btn.clicked.connect(self._reset_archived_tournaments)

        reset_tournaments_btn = QPushButton("Supprimer tous les tournois")
        reset_tournaments_btn.setObjectName("DangerButton")
        reset_tournaments_btn.clicked.connect(self._reset_tournaments)

        reset_players_btn = QPushButton("Supprimer tous les joueurs")
        reset_players_btn.setObjectName("DangerButton")
        reset_players_btn.clicked.connect(self._reset_players)

        buttons_layout.addWidget(reset_archived_btn)
        buttons_layout.addWidget(reset_tournaments_btn)
        buttons_layout.addWidget(reset_players_btn)
        buttons_layout.addStretch()

        layout.addLayout(buttons_layout)

        # Mettre à jour les stats
        self._refresh_stats()

        return frame

    def _build_about_section(self) -> QFrame:
        """Construit la section À propos."""
        frame = QFrame()
        frame.setObjectName("SettingsSection")

        layout = QVBoxLayout(frame)
        layout.setSpacing(12)

        title = QLabel("À propos")
        title.setObjectName("SettingsSectionTitle")
        layout.addWidget(title)

        app_name = QLabel("MagicTable — Tournament Manager")
        app_name.setObjectName("SettingsAppName")
        layout.addWidget(app_name)

        version = QLabel("Version 1.0.0")
        version.setObjectName("SettingsVersion")
        layout.addWidget(version)

        description = QLabel(
            "Application de gestion de tournois Magic: The Gathering.\n"
            "Conçue pour organiser des tournois Commander avec\n"
            "gestion des tables, classements et statistiques."
        )
        description.setObjectName("SettingsDescription")
        layout.addWidget(description)

        return frame

    def _refresh_stats(self):
        """Rafraîchit les statistiques affichées."""
        tournaments = TournamentStorage.load()
        players = RegularPlayerStorage.load()

        t_count = len(tournaments)
        p_count = len(players)

        self.tournaments_count.setText(
            f"{t_count} tournoi{'s' if t_count != 1 else ''}"
        )
        self.players_count.setText(
            f"{p_count} joueur{'s' if p_count != 1 else ''} permanent{'s' if p_count != 1 else ''}"
        )

    def _reset_archived_tournaments(self):
        """Supprime uniquement les tournois archivés après confirmation."""
        all_tournaments = TournamentStorage.load()
        archived_count = sum(1 for t in all_tournaments if t.get("archived", False))

        if archived_count == 0:
            QMessageBox.information(
                self,
                "Aucun tournoi archivé",
                "Il n'y a aucun tournoi archivé à supprimer."
            )
            return

        reply = QMessageBox.warning(
            self,
            "Supprimer les tournois archivés",
            f"Cette action est irréversible !\n\n"
            f"{archived_count} tournoi{'s' if archived_count > 1 else ''} archivé{'s' if archived_count > 1 else ''} "
            f"{'seront supprimés' if archived_count > 1 else 'sera supprimé'}.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        remaining = [t for t in all_tournaments if not t.get("archived", False)]
        TournamentStorage.save(remaining)
        self._refresh_stats()
        self.tournaments_cleared.emit()

        QMessageBox.information(
            self,
            "Tournois archivés supprimés",
            f"{archived_count} tournoi{'s' if archived_count > 1 else ''} archivé{'s' if archived_count > 1 else ''} "
            f"{'ont été supprimés' if archived_count > 1 else 'a été supprimé'}."
        )

    def _reset_tournaments(self):
        """Supprime tous les tournois après confirmation."""
        reply = QMessageBox.warning(
            self,
            "Supprimer tous les tournois",
            "Cette action est irréversible !\n\n"
            "Tous les tournois (actifs et archivés) seront supprimés.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        TournamentStorage.save([])
        self._refresh_stats()
        self.tournaments_cleared.emit()

        QMessageBox.information(
            self,
            "Tournois supprimés",
            "Tous les tournois ont été supprimés."
        )

    def _reset_players(self):
        """Supprime tous les joueurs permanents après confirmation."""
        reply = QMessageBox.warning(
            self,
            "Supprimer tous les joueurs",
            "Cette action est irréversible !\n\n"
            "Tous les joueurs permanents et leurs statistiques seront supprimés.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        RegularPlayerStorage.save([])
        self._refresh_stats()

        QMessageBox.information(
            self,
            "Joueurs supprimés",
            "Tous les joueurs permanents ont été supprimés."
        )

    def showEvent(self, event):
        """Rafraîchit les stats quand la vue est affichée."""
        super().showEvent(event)
        self._refresh_stats()

    def get_timer_duration(self) -> int:
        """Retourne la durée du timer en minutes."""
        return self.timer_spinbox.value()
