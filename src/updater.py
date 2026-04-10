"""
Système de mise à jour automatique via GitHub Releases.

- UpdateChecker : QThread qui interroge l'API GitHub au démarrage
- Updater       : télécharge le nouvel exécutable et lance le script de remplacement
"""

import sys
import os
import ssl
import json
import stat
import subprocess
import urllib.request
import urllib.error
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from version import __version__, GITHUB_REPO


def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _is_packaged() -> bool:
    return getattr(sys, "frozen", False)


def _is_newer(latest: str, current: str) -> bool:
    try:
        return [int(x) for x in latest.split(".")] > [int(x) for x in current.split(".")]
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# UpdateChecker
# ---------------------------------------------------------------------------

class UpdateChecker(QThread):
    update_available = Signal(str, str)  # (version, download_url)
    check_failed     = Signal()

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
                return

            # Cherche l'asset correspondant à la plateforme courante
            assets = data.get("assets", [])
            url = _pick_asset(assets)
            if url:
                self.update_available.emit(tag, url)

        except Exception:
            pass


def _pick_asset(assets: list) -> str | None:
    """
    Retourne l'URL de téléchargement de l'asset le plus adapté à la plateforme.
    Windows → préfère .exe
    Linux   → préfère binaire Linux (sans extension ou .bin), accepte aussi .exe
    """
    if sys.platform == "win32":
        for a in assets:
            if a.get("name", "").lower().endswith(".exe"):
                return a["browser_download_url"]
    else:
        # Linux : préfère un asset nommé explicitement pour Linux
        for a in assets:
            name = a.get("name", "").lower()
            if "linux" in name:
                return a["browser_download_url"]
        # Fallback : binaire sans extension nommé "magictable"
        for a in assets:
            name = a.get("name", "").lower()
            if name == "magictable" or name.endswith(".bin"):
                return a["browser_download_url"]
        # Dernier recours : .exe (sera renommé lors de l'installation)
        for a in assets:
            if a.get("name", "").lower().endswith(".exe"):
                return a["browser_download_url"]
    return None


# ---------------------------------------------------------------------------
# Updater
# ---------------------------------------------------------------------------

class Updater(QThread):
    progress = Signal(int, int)
    finished = Signal()
    error    = Signal(str)

    def __init__(self, download_url: str, parent=None):
        super().__init__(parent)
        self._url = download_url

    def run(self):
        if not _is_packaged():
            self.error.emit("La mise à jour automatique nécessite l'application packagée.")
            return

        try:
            current_exe = Path(sys.executable)

            if sys.platform == "win32":
                self._run_windows(current_exe)
            else:
                self._run_linux(current_exe)

        except Exception as e:
            self.error.emit(str(e))

    # ── Windows ───────────────────────────────────────────────────────────────

    def _run_windows(self, current_exe: Path):
        new_exe  = current_exe.parent / "MagicTable_new.exe"
        bat_path = current_exe.parent / "update.bat"

        self._download(new_exe)

        bat = (
            "@echo off\n"
            "timeout /t 2 /nobreak > nul\n"
            f'move /y "{new_exe}" "{current_exe}"\n'
            f'start "" "{current_exe}"\n'
            'del "%~f0"\n'
        )
        bat_path.write_text(bat, encoding="utf-8")
        self.finished.emit()

    # ── Linux ─────────────────────────────────────────────────────────────────

    def _run_linux(self, current_exe: Path):
        new_exe = current_exe.parent / "MagicTable_new"
        sh_path = current_exe.parent / "update.sh"

        self._download(new_exe)

        # Rendre le nouveau binaire exécutable
        new_exe.chmod(new_exe.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

        sh = (
            "#!/bin/sh\n"
            "sleep 2\n"
            f'mv -f "{new_exe}" "{current_exe}"\n'
            f'chmod +x "{current_exe}"\n'
            f'"{current_exe}" &\n'
            f'rm -- "$0"\n'
        )
        sh_path.write_text(sh, encoding="utf-8")
        sh_path.chmod(sh_path.stat().st_mode | stat.S_IEXEC)
        self.finished.emit()

    # ── Téléchargement commun ─────────────────────────────────────────────────

    def _download(self, dest: Path):
        req = urllib.request.Request(
            self._url,
            headers={"User-Agent": "MagicTable-Updater/1.0"},
        )
        with urllib.request.urlopen(req, context=_ssl_context()) as resp:
            total    = int(resp.headers.get("Content-Length", 0))
            received = 0
            with open(dest, "wb") as f:
                while chunk := resp.read(65536):
                    f.write(chunk)
                    received += len(chunk)
                    self.progress.emit(received, total)

    # ── Application de la mise à jour ─────────────────────────────────────────

    def apply(self):
        if not _is_packaged():
            return

        exe_dir = Path(sys.executable).parent

        if sys.platform == "win32":
            bat_path = exe_dir / "update.bat"
            if bat_path.exists():
                os.startfile(str(bat_path))
        else:
            sh_path = exe_dir / "update.sh"
            if sh_path.exists():
                subprocess.Popen(["/bin/sh", str(sh_path)],
                                 close_fds=True,
                                 start_new_session=True)

        sys.exit(0)
