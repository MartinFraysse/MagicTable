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

        # Section Notation
        scoring_section = self._build_scoring_section()
        content_layout.addWidget(scoring_section)

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

    def _build_scoring_section(self) -> QFrame:
        """Construit la section d'explication des systèmes de notation."""
        frame = QFrame()
        frame.setObjectName("SettingsSection")

        layout = QVBoxLayout(frame)
        layout.setSpacing(16)

        title = QLabel("Systèmes de notation par format")
        title.setObjectName("SettingsSectionTitle")
        layout.addWidget(title)

        # --- Commander ---
        commander_block = self._build_scoring_block(
            "👑 Commander (tables de 3-4 joueurs)",
            [
                ("Points par manche", [
                    "🥇 1er  →  3 points",
                    "🥈 2ème →  2 points",
                    "🥉 3ème / 4ème  →  1 point",
                ]),
                ("Départage — Robustesse", [
                    "Somme pondérée du rang actuel de chaque adversaire rencontré",
                    "Formule : pour chaque adversaire → (N − rang adversaire), où N = nb de joueurs",
                    "Plus tu affrontes des joueurs bien classés, plus ta robustesse est élevée",
                    "Recalculée automatiquement après chaque round",
                ]),
            ]
        )
        layout.addWidget(commander_block)

        # --- Formats 1v1 ---
        standard_block = self._build_scoring_block(
            "⚔️ Formats 1v1 — Swiss pairing (Duel Commander, AP, Pokémon…)",
            [
                ("Points par manche", [
                    "🏆 Victoire  →  3 points",
                    "⚖️ Match nul  →  1 point",
                    "❌ Défaite  →  0 point",
                ]),
                ("Départage (ordre de priorité — système officiel MTG)", [
                    "1. OMW% (Opponent Match Win %) — % de victoires de tes adversaires",
                    "2. GW% (Game Win %) — % de parties gagnées sur l'ensemble de tes games",
                    "3. OGW% (Opponent Game Win %) — % de parties gagnées par tes adversaires",
                ]),
                ("Précisions OMW% / GW%", [
                    "OMW% : chaque adversaire est compté à minimum 33% même s'il a moins",
                    "GW%  : calculé si les scores BO3 (2-0, 2-1…) ont été saisis, sinon « — »",
                ]),
            ]
        )
        layout.addWidget(standard_block)

        return frame

    def _build_scoring_block(self, title: str, sections: list) -> QFrame:
        """Construit un bloc de notation pour un format."""
        block = QFrame()
        block.setObjectName("ScoringBlock")

        layout = QVBoxLayout(block)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 12, 12, 12)

        title_label = QLabel(title)
        title_label.setObjectName("ScoringFormatTitle")
        layout.addWidget(title_label)

        for section_title, lines in sections:
            sub_title = QLabel(section_title)
            sub_title.setObjectName("ScoringSubTitle")
            layout.addWidget(sub_title)

            for line in lines:
                line_label = QLabel(f"  {line}")
                line_label.setObjectName("ScoringLine")
                layout.addWidget(line_label)

        return block

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
