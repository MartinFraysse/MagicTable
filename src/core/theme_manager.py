"""Gestionnaire de thèmes pour MagicTable."""

import json
from pathlib import Path
from typing import Literal

ThemeType = Literal["dark", "light"]

# Répertoire de l'application
APP_DIR = Path(__file__).parent.parent
CONFIG_FILE = APP_DIR / "data" / "config.json"


class ThemeManager:
    """Singleton pour gérer les thèmes de l'application."""

    _instance = None
    _app = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._current_theme: ThemeType = self._load_preference()

    def set_app(self, app):
        """Définit l'application Qt pour permettre le changement de thème."""
        self._app = app

    def get_theme(self) -> ThemeType:
        """Retourne le thème actuel."""
        return self._current_theme

    def set_theme(self, theme: ThemeType):
        """Change le thème et l'applique immédiatement."""
        if theme not in ("dark", "light"):
            return

        self._current_theme = theme
        self._save_preference()

        if self._app:
            stylesheet = self.load_theme_stylesheet()
            self._app.setStyleSheet(stylesheet)

    def load_theme_stylesheet(self) -> str:
        """Charge et concatène tous les fichiers QSS du thème actuel."""
        prefix = "dark_green" if self._current_theme == "dark" else "light_green"

        files = [
            f"{prefix}_main.qss",
            f"{prefix}_dashboard.qss",
            f"{prefix}_tournament.qss",
            f"{prefix}_player.qss",
            f"{prefix}_stats.qss",
            f"{prefix}_setting.qss",
            f"{prefix}_widget.qss",
        ]

        css = ""
        styles_dir = APP_DIR / "styles"

        for filename in files:
            filepath = styles_dir / filename
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    css += f.read() + "\n"
            except FileNotFoundError:
                print(f"⚠️ Stylesheet non trouvé: {filepath}")

        return css

    def _load_preference(self) -> ThemeType:
        """Charge la préférence de thème depuis le fichier de config."""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    theme = config.get("theme", "dark")
                    if theme in ("dark", "light"):
                        return theme
        except json.JSONDecodeError as e:
            print(f"⚠️ Erreur de lecture de la config (JSON invalide): {e}")
        except IOError as e:
            print(f"⚠️ Erreur de lecture de la config: {e}")
        return "dark"

    def _save_preference(self):
        """Sauvegarde la préférence de thème dans le fichier de config."""
        config = {}

        # Charger la config existante si elle existe
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    config = json.load(f)
        except json.JSONDecodeError as e:
            print(f"⚠️ Config corrompue, sera réinitialisée: {e}")
        except IOError as e:
            print(f"⚠️ Erreur de lecture config: {e}")

        config["theme"] = self._current_theme

        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        except IOError as e:
            print(f"⚠️ Impossible de sauvegarder la config: {e}")


# Instance globale
theme_manager = ThemeManager()
