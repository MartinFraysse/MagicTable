from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QFrame, QPushButton, QSpinBox, QMessageBox,
    QScrollArea, QProgressBar
)
from PySide6.QtCore import Qt, Signal

from storage.tournaments import TournamentStorage
from storage.regular_players import RegularPlayerStorage
from storage.commanders import CommanderStorage
from version import __version__
from updater import UpdateChecker, Updater, _is_packaged


class SettingsView(QWidget):
    """Vue des paramètres de l'application."""

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

        # Section Mise à jour
        update_section = self._build_update_section()
        content_layout.addWidget(update_section)

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

        # --- Formats 1v1 Swiss ---
        standard_block = self._build_scoring_block(
            "⚔️ Formats 1v1 Swiss — Duel Commander, Draft, AP, Pokémon",
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
                    "Anti-rematch : le Swiss évite de faire s'affronter deux fois les mêmes joueurs",
                ]),
            ]
        )
        layout.addWidget(standard_block)

        # --- Bracket éliminatoire ---
        bracket_block = self._build_scoring_block(
            "🏅 Bracket éliminatoire (tous formats)",
            [
                ("Fonctionnement", [
                    "Disponible en fin de tournoi Swiss ou à tout moment",
                    "Tableau à élimination directe généré à partir du classement actuel",
                    "Les résultats du bracket n'affectent pas le classement Swiss",
                ]),
            ]
        )
        layout.addWidget(bracket_block)

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

        reset_commanders_btn = QPushButton("Supprimer tous les commandants")
        reset_commanders_btn.setObjectName("DangerButton")
        reset_commanders_btn.clicked.connect(self._reset_commanders)

        buttons_layout.addWidget(reset_archived_btn)
        buttons_layout.addWidget(reset_tournaments_btn)
        buttons_layout.addWidget(reset_players_btn)
        buttons_layout.addWidget(reset_commanders_btn)
        buttons_layout.addStretch()

        layout.addLayout(buttons_layout)

        # Mettre à jour les stats
        self._refresh_stats()

        return frame

    def _build_update_section(self) -> QFrame:
        """Section de mise à jour manuelle."""
        frame = QFrame()
        frame.setObjectName("SettingsSection")

        layout = QVBoxLayout(frame)
        layout.setSpacing(12)

        title = QLabel("Mise à jour")
        title.setObjectName("SettingsSectionTitle")
        layout.addWidget(title)

        # Version actuelle
        row = QHBoxLayout()
        ver_label = QLabel("Version actuelle :")
        ver_label.setObjectName("SettingsLabel")
        row.addWidget(ver_label)
        self._current_version_lbl = QLabel(f"v{__version__}")
        self._current_version_lbl.setObjectName("SettingsVersion")
        row.addWidget(self._current_version_lbl)
        row.addStretch()
        layout.addLayout(row)

        # Statut + bouton vérifier
        check_row = QHBoxLayout()
        self._update_status_lbl = QLabel("")
        self._update_status_lbl.setObjectName("SettingsHint")
        check_row.addWidget(self._update_status_lbl, 1)

        self._check_btn = QPushButton("🔍 Vérifier les mises à jour")
        self._check_btn.setObjectName("PrimaryButton")
        self._check_btn.setCursor(Qt.PointingHandCursor)
        self._check_btn.clicked.connect(self._check_update)
        check_row.addWidget(self._check_btn)
        layout.addLayout(check_row)

        # Barre de progression (cachée par défaut)
        self._update_progress = QProgressBar()
        self._update_progress.setObjectName("UpdateProgressBar")
        self._update_progress.setTextVisible(False)
        self._update_progress.setFixedHeight(8)
        self._update_progress.hide()
        layout.addWidget(self._update_progress)

        # Bouton télécharger (caché jusqu'à ce qu'une MAJ soit trouvée)
        self._download_btn = QPushButton("⬇  Télécharger et installer")
        self._download_btn.setObjectName("PrimaryButton")
        self._download_btn.setCursor(Qt.PointingHandCursor)
        self._download_btn.clicked.connect(self._download_update)
        self._download_btn.hide()
        layout.addWidget(self._download_btn)

        self._checker: UpdateChecker | None = None
        self._updater: Updater | None = None
        self._pending_url: str = ""

        return frame

    def _check_update(self):
        self._check_btn.setEnabled(False)
        self._check_btn.setText("Vérification…")
        self._update_status_lbl.setText("")
        self._download_btn.hide()
        self._update_progress.hide()

        self._checker = UpdateChecker()
        self._checker.update_available.connect(self._on_update_found)
        self._checker.check_failed.connect(self._on_check_failed)
        self._checker.finished.connect(self._on_check_done)
        self._checker.start()

    def _on_check_done(self):
        """Le thread a terminé sans trouver de MAJ."""
        self._check_btn.setEnabled(True)
        self._check_btn.setText("🔍 Vérifier les mises à jour")
        if not self._pending_url:
            self._update_status_lbl.setText("✅ Vous êtes à jour !")

    def _on_update_found(self, version: str, url: str):
        self._pending_url = url
        self._update_status_lbl.setText(f"🆕 Version v{version} disponible !")
        self._download_btn.show()

    def _on_check_failed(self):
        self._update_status_lbl.setText("❌ Impossible de vérifier (pas de connexion ?)")

    def _download_update(self):
        if not _is_packaged():
            QMessageBox.information(self, "Info",
                "La mise à jour automatique fonctionne uniquement\n"
                "avec la version .exe packagée.")
            return

        self._download_btn.setEnabled(False)
        self._download_btn.setText("Téléchargement…")
        self._update_progress.setValue(0)
        self._update_progress.show()

        self._updater = Updater(self._pending_url, self)
        self._updater.progress.connect(self._on_dl_progress)
        self._updater.finished.connect(self._on_dl_finished)
        self._updater.error.connect(self._on_dl_error)
        self._updater.start()

    def _on_dl_progress(self, received: int, total: int):
        if total > 0:
            self._update_progress.setValue(int(received / total * 100))
            self._update_status_lbl.setText(
                f"⬇  {received/1_048_576:.1f} / {total/1_048_576:.1f} Mo"
            )

    def _on_dl_finished(self):
        self._update_progress.setValue(100)
        self._update_status_lbl.setText("✅ Téléchargement terminé !")
        self._download_btn.setText("🔄 Redémarrer et installer")
        self._download_btn.setEnabled(True)
        self._download_btn.clicked.disconnect()
        self._download_btn.clicked.connect(self._updater.apply)

    def _on_dl_error(self, msg: str):
        self._update_status_lbl.setText(f"❌ Erreur : {msg}")
        self._download_btn.setEnabled(True)
        self._download_btn.setText("⬇  Réessayer")

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

        version = QLabel(f"Version {__version__}")
        version.setObjectName("SettingsVersion")
        layout.addWidget(version)

        description = QLabel(
            "Application de gestion de tournois Magic: The Gathering\n"
            "et autres jeux de cartes. Supporte Commander, Duel Commander,\n"
            "Draft, AP, Pokémon — avec Swiss pairing, bracket éliminatoire,\n"
            "classements, statistiques et export PDF."
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

    def _reset_commanders(self):
        """Supprime tous les commandants après confirmation."""
        commanders = CommanderStorage.load()
        count = len(commanders)

        if count == 0:
            QMessageBox.information(self, "Aucun commandant",
                "Il n'y a aucun commandant à supprimer.")
            return

        reply = QMessageBox.warning(
            self,
            "Supprimer tous les commandants",
            f"Cette action est irréversible !\n\n"
            f"{count} commandant{'s' if count > 1 else ''} et leurs images seront supprimés.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return

        CommanderStorage.save([])
        QMessageBox.information(self, "Commandants supprimés",
            f"{count} commandant{'s' if count > 1 else ''} supprimé{'s' if count > 1 else ''}.")

    def showEvent(self, event):
        """Rafraîchit les stats quand la vue est affichée."""
        super().showEvent(event)
        self._refresh_stats()

    def get_timer_duration(self) -> int:
        """Retourne la durée du timer en minutes."""
        return self.timer_spinbox.value()
