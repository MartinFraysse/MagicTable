import sys
import shutil
from pathlib import Path
from ui.main_window import MainWindow
from PySide6.QtWidgets import QApplication, QStyleFactory
from PySide6.QtGui import QIcon


def get_resource_dir() -> Path:
    """
    Retourne le répertoire contenant les ressources read-only (assets, styles).
    - Mode packagé (PyInstaller) : sys._MEIPASS  (fichiers extraits du bundle)
    - Mode développement         : dossier de app.py
    """
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).parent


# Répertoire racine de l’application (où se trouve app.py)
APP_DIR = get_resource_dir()

def install_desktop_entry():
    """Installe l’icône et le .desktop dans ~/.local/share/ pour Wayland/Linux."""
    import subprocess
    icon_src = APP_DIR / "assets" / "MT_logo.png"
    if not icon_src.exists():
        return

    icon_dst = Path.home() / ".local/share/icons/hicolor/256x256/apps/MagicTable.png"
    desktop_dst = Path.home() / ".local/share/applications/MagicTable.desktop"

    icon_dst.parent.mkdir(parents=True, exist_ok=True)
    desktop_dst.parent.mkdir(parents=True, exist_ok=True)

    shutil.copy2(icon_src, icon_dst)

    desktop_content = f"""[Desktop Entry]
Name=MagicTable
Exec=python {APP_DIR / "app.py"}
Icon=MagicTable
Type=Application
Categories=Game;
"""
    desktop_dst.write_text(desktop_content)

    subprocess.run(["gtk-update-icon-cache", "-f", "-t", str(icon_dst.parent.parent.parent)], capture_output=True)
    subprocess.run(["update-desktop-database", str(desktop_dst.parent)], capture_output=True)

def _pull_from_server() -> None:
    """Synchronise les données depuis le serveur au démarrage (silencieux si hors-ligne)."""
    try:
        from sync.server_client import pull_all
        from storage.base import DATA_DIR
        result = pull_all(DATA_DIR)
        synced = result["synced"]
        failed = result["failed"]
        if synced:
            print(f"✅ Sync serveur : {', '.join(synced)}")
        if failed:
            print(f"⚠️  Sync serveur — ressources manquantes : {', '.join(failed)}")
        if not synced:
            print("⚠️  Serveur inaccessible, démarrage avec les données locales")
    except Exception as e:
        print(f"⚠️  Sync serveur ignorée : {e}")


def main():
    _pull_from_server()
    app = QApplication(sys.argv)

    app.setStyle(QStyleFactory.create("Fusion"))

    # 🔑 IDENTITÉ DE L’APP (OBLIGATOIRE POUR WAYLAND)
    app.setApplicationName("MagicTable")
    app.setDesktopFileName("MagicTable")

    if sys.platform == "win32":
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MagicTable")
    else:
        install_desktop_entry()

    icon = QIcon(str(APP_DIR / "assets" / "MT_logo.png"))
    app.setWindowIcon(icon)

    # Charger le thème
    app.setStyleSheet(load_qss(
        "styles/dark_green_dashboard.qss",
        "styles/dark_green_tournament.qss",
        "styles/dark_green_player.qss",
        "styles/dark_green_stats.qss",
        "styles/dark_green_setting.qss",
        "styles/dark_green_main.qss",
        "styles/dark_green_widget.qss",
        "styles/dark_green_league.qss",
    ))

    window = MainWindow()
    window._toggle_fullscreen()

    sys.exit(app.exec())

def load_qss(*paths):
    css = ""
    for path in paths:
        full_path = APP_DIR / path
        try:
            with open(full_path, "r") as f:
                css += f.read() + "\n"
        except FileNotFoundError:
            print(f"⚠️ Stylesheet non trouvé: {full_path}")
    return css

if __name__ == "__main__":
    main()
