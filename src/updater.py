"""
Système de mise à jour automatique via GitHub Releases.

- UpdateChecker : QThread qui interroge l'API GitHub au démarrage
- Updater       : télécharge le nouvel .exe et lance le script de remplacement
"""

import sys
import os
import ssl
import json
import urllib.request
import urllib.error
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from version import __version__, GITHUB_REPO


def _ssl_context() -> ssl.SSLContext:
    """
    Retourne un contexte SSL fiable dans un bundle PyInstaller.
    Utilise certifi si disponible, sinon le store système.
    """
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_newer(latest: str, current: str) -> bool:
    """Compare deux versions X.Y.Z. Retourne True si latest > current."""
    try:
        return [int(x) for x in latest.split(".")] > [int(x) for x in current.split(".")]
    except ValueError:
        return False


def _is_packaged() -> bool:
    """Retourne True si l'app tourne depuis un .exe PyInstaller."""
    return getattr(sys, "frozen", False)


# ---------------------------------------------------------------------------
# UpdateChecker — thread de vérification
# ---------------------------------------------------------------------------

class UpdateChecker(QThread):
    """
    Thread léger lancé au démarrage.
    Émet update_available(nouvelle_version, url_download) si une MAJ existe.
    Ne fait rien en cas d'erreur réseau (timeout, pas d'internet…).
    """

    update_available = Signal(str, str)  # (version, download_url)
    check_failed     = Signal()          # réseau indisponible / erreur

    def run(self):
        try:
            api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
            req = urllib.request.Request(
                api_url,
                headers={"User-Agent": "MagicTable-Updater/1.0"},
            )
            with urllib.request.urlopen(req, timeout=6, context=_ssl_context()) as resp:
                data = json.loads(resp.read().decode())

            tag = data.get("tag_name", "").lstrip("v")
            if not tag or not _is_newer(tag, __version__):
                return  # Déjà à jour

            # Cherche un asset .exe dans la release
            for asset in data.get("assets", []):
                name: str = asset.get("name", "")
                if name.lower().endswith(".exe"):
                    self.update_available.emit(tag, asset["browser_download_url"])
                    return

        except Exception:
            pass  # Silencieux — pas d'internet, token expiré, etc.


# ---------------------------------------------------------------------------
# Updater — téléchargement + installation
# ---------------------------------------------------------------------------

class Updater(QThread):
    """
    Thread de téléchargement.
    Émet progress(bytes_reçus, total) pendant le téléchargement,
    puis finished() quand le script de mise à jour est prêt à être lancé.
    """

    progress = Signal(int, int)   # (bytes_recus, total)
    finished = Signal()
    error    = Signal(str)

    def __init__(self, download_url: str, parent=None):
        super().__init__(parent)
        self._url = download_url

    def run(self):
        if not _is_packaged():
            self.error.emit("La mise à jour automatique nécessite le .exe packagé.")
            return

        try:
            current_exe = Path(sys.executable)
            new_exe     = current_exe.parent / "MagicTable_new.exe"
            bat_path    = current_exe.parent / "update.bat"

            # ── Téléchargement ────────────────────────────────────────────
            def _on_progress(block_count, block_size, total_size):
                received = min(block_count * block_size, total_size)
                self.progress.emit(received, total_size)

            req_dl = urllib.request.Request(
                self._url,
                headers={"User-Agent": "MagicTable-Updater/1.0"},
            )
            with urllib.request.urlopen(req_dl, context=_ssl_context()) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                received = 0
                with open(new_exe, "wb") as f:
                    while chunk := resp.read(65536):
                        f.write(chunk)
                        received += len(chunk)
                        self.progress.emit(received, total)

            # ── Script de remplacement (Windows .bat) ─────────────────────
            # Attend 2s (temps que le process Qt se ferme), puis remplace
            bat = (
                "@echo off\n"
                "timeout /t 2 /nobreak > nul\n"
                f'move /y "{new_exe}" "{current_exe}"\n'
                f'start "" "{current_exe}"\n'
                'del "%~f0"\n'
            )
            bat_path.write_text(bat, encoding="utf-8")

            self.finished.emit()

        except Exception as e:
            self.error.emit(str(e))

    def apply(self):
        """
        Appelle cette méthode après finished() pour lancer le script
        et quitter l'application.
        """
        if not _is_packaged():
            return
        bat_path = Path(sys.executable).parent / "update.bat"
        if bat_path.exists():
            os.startfile(str(bat_path))
        sys.exit(0)
