import sys
from pathlib import Path
from ui.main_window import MainWindow
from PySide6.QtWidgets import QApplication, QStyleFactory

# Répertoire racine de l'application (où se trouve app.py)
APP_DIR = Path(__file__).parent

def main():
    app = QApplication(sys.argv)

    app.setStyle(QStyleFactory.create("Fusion"))

    # 🔑 IDENTITÉ DE L’APP (OBLIGATOIRE POUR WAYLAND)
    app.setApplicationName("MagicTable")
    app.setDesktopFileName("MagicTable")

    # Charger le thème
    app.setStyleSheet(load_qss(
        "styles/dark_green_dashboard.qss",
        "styles/dark_green_tournament.qss",
        "styles/dark_green_player.qss",
        "styles/dark_green_stats.qss",
        "styles/dark_green_setting.qss",
        "styles/dark_green_main.qss",
        "styles/dark_green_widget.qss",
    ))

    """app.setStyleSheet(load_qss("styles/dark_green_widget.qss"))"""
    
    window = MainWindow()
    window.show()

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
