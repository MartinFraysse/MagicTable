from PySide6.QtWidgets import (
    QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QFrame,
    QButtonGroup, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QStackedWidget
from PySide6.QtGui import QPixmap

from ui.tournaments.tournaments_view_main import TournamentViewMain
from ui.players_view import PlayersView
from ui.matches_view import MatchesView
from ui.settings_view import SettingsView
from ui.dashboard.dashboard_view_main import DashboardViewMain

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Permet aux backgrounds QSS de s’appliquer correctement
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.setWindowTitle("MagicTable — Tournament Manager")

        self.resize(1380, 840)
        self.setMinimumSize(1380, 920)
        self.setMaximumSize(1380, 920)

        # === CENTRAL ROOT ===
        central = QWidget()
        central.setAttribute(Qt.WA_StyledBackground, True)
        self.setCentralWidget(central)

        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # === SIDEBAR ===
        self.sidebar = self._build_sidebar()
        root_layout.addWidget(self.sidebar)

        # === CONTENT CONTAINER ===
        self.content_container = self._build_content_container()
        root_layout.addWidget(self.content_container)

        # === CONNECT NAVIGATION ===
        for index, btn in enumerate(self.nav_buttons):
            btn.clicked.connect(
                lambda checked, i=index: self.stack.setCurrentIndex(i)
            )

        self.tournaments_view.round_started.connect(
            self.start_tournament
        )

        # Sauvegarder quand le dashboard modifie le tournoi
        self.dashboard_view.tournament_changed.connect(
            self.tournaments_view.save_tournaments
        )

        # Archiver un tournoi
        self.dashboard_view.tournament_archived.connect(
            self.tournaments_view.on_tournament_archived
        )

    # ========================
    # Sidebar
    # ========================
    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setAttribute(Qt.WA_StyledBackground, True)
        sidebar.setFixedWidth(260)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # ===== Logo (centré, texte dessous) =====
        logo_container = QWidget()
        logo_layout = QVBoxLayout(logo_container)
        logo_layout.setContentsMargins(0, 0, 0, 0)
        logo_layout.setSpacing(10)
        logo_layout.setAlignment(Qt.AlignHCenter)

        # Logo image
        logo_icon = QLabel()
        logo_icon.setObjectName("LogoIcon")
        logo_icon.setAlignment(Qt.AlignHCenter)

        pixmap = QPixmap("assets/MT_logo.png")
        logo_icon.setPixmap(
            pixmap.scaled(
                112, 112,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
        )
        logo_icon.setFixedSize(112, 112)

        # Logo text
        logo_text = QLabel("MagicTable")
        logo_text.setObjectName("Logo")
        logo_text.setAlignment(Qt.AlignHCenter)

        logo_layout.addWidget(logo_icon)
        logo_layout.addWidget(logo_text)

        layout.addWidget(logo_container)
        layout.addSpacing(50)   # 👈 descend les menus

        # ===== Navigation =====
        self.nav_group = QButtonGroup()
        self.nav_group.setExclusive(True)

        self.nav_buttons = []

        for icon, name in [
            ("📊", "Dashboard"),
            ("🏆", "Tournois"),
            ("👥", "Joueurs"),
            ("⚔️", "Matchs"),
            ("⚙️", "Paramètres"),
        ]:
            btn = QPushButton(f"{icon}  {name}")
            btn.setObjectName("NavButton")
            btn.setCheckable(True)
            btn.setMinimumHeight(44)
            btn.setCursor(Qt.PointingHandCursor)

            self.nav_group.addButton(btn)
            self.nav_buttons.append(btn)
            layout.addWidget(btn)

        # Actif par défaut
        self.nav_group.buttons()[0].setChecked(True)

        layout.addStretch()

        quit_btn = QPushButton("⏻  Quitter")
        quit_btn.setObjectName("QuitButton")
        quit_btn.setMinimumHeight(44)

        layout.addWidget(quit_btn)

        return sidebar

    # ========================
    # Content container
    # ========================
    def _build_content_container(self):
        container = QFrame()
        container.setObjectName("ContentContainer")
        container.setAttribute(Qt.WA_StyledBackground, True)

        container.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )

        layout = QVBoxLayout(container)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(0)

        # ===== STACK DE VUES =====
        self.stack = QStackedWidget()
        self.stack.setObjectName("MainStack")
        self.stack.setAttribute(Qt.WA_StyledBackground, True)

        self.dashboard_view = DashboardViewMain()
        self.tournaments_view = TournamentViewMain()
        self.players_view = PlayersView()
        self.matches_view = MatchesView()
        self.settings_view = SettingsView()

        self.stack.addWidget(self.dashboard_view)
        self.stack.addWidget(self.tournaments_view)
        self.stack.addWidget(self.players_view)
        self.stack.addWidget(self.matches_view)
        self.stack.addWidget(self.settings_view)

        layout.addWidget(self.stack)

        return container

    def start_tournament(self, tournament: Tournament):
        self.stack.setCurrentIndex(0)
        self.nav_buttons[0].setChecked(True)
        
        self.dashboard_view.set_current_round(tournament)