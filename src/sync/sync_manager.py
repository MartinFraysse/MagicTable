"""
Gestionnaire de synchronisation périodique avec le serveur.

- Toutes les INTERVAL_MS, compare les données serveur avec le cache local.
- Si une différence est détectée, met à jour le cache local et émet `data_changed`
  pour que l'UI puisse se rafraîchir.
"""

import json
import threading
from pathlib import Path

from PySide6.QtCore import QObject, QTimer, Signal

INTERVAL_MS = 5_000  # 5 secondes

# Mapping resource API → fichier local (doit rester cohérent avec api.py)
_FILENAMES: dict[str, str] = {
    "players":     "regular_players.json",
    "tournaments": "tournaments.json",
    "leagues":     "leagues.json",
    "commanders":  "commanders.json",
}


class SyncManager(QObject):
    """
    Lance un QTimer qui vérifie périodiquement si le serveur a des données
    plus récentes que le cache local. Émet `data_changed` si au moins une
    ressource a été mise à jour.

    Usage :
        self.sync_manager = SyncManager(DATA_DIR, parent=self)
        self.sync_manager.data_changed.connect(self._on_data_synced)
        self.sync_manager.start()
    """

    data_changed = Signal()

    def __init__(self, data_dir: Path, interval_ms: int = INTERVAL_MS, parent=None):
        super().__init__(parent)
        self._data_dir = data_dir
        self._busy = False  # Évite les chevauchements si le serveur est lent

        self._timer = QTimer(self)
        self._timer.setInterval(interval_ms)
        self._timer.timeout.connect(self._on_tick)

    def start(self):
        self._timer.start()

    def stop(self):
        self._timer.stop()

    # ── Interne ───────────────────────────────────────────────────────────────

    def _on_tick(self):
        """Appelé dans le thread Qt principal — délègue le réseau à un thread."""
        if self._busy:
            return
        self._busy = True
        threading.Thread(target=self._check_and_update, daemon=True).start()

    def _check_and_update(self):
        """Thread réseau : fetch → compare → écrit si différent → signal."""
        try:
            self._do_check()
        finally:
            self._busy = False

    def _do_check(self):
        try:
            from sync.server_client import fetch, is_configured
        except ImportError:
            return

        if not is_configured():
            return

        changed = False

        for resource, filename in _FILENAMES.items():
            server_data = fetch(resource, timeout=5)
            if server_data is None:
                continue  # Serveur inaccessible → on garde le cache local

            local_path = self._data_dir / filename
            try:
                local_data = (
                    json.loads(local_path.read_text(encoding="utf-8"))
                    if local_path.exists()
                    else []
                )
            except Exception:
                local_data = []

            # Garde-fou : ne jamais écraser des données locales non vides
            # par une liste vide venant du serveur.
            if not server_data and local_data:
                continue

            # Comparer (indépendant de l'ordre des clés)
            if json.dumps(server_data, sort_keys=True) != json.dumps(local_data, sort_keys=True):
                try:
                    # Pour les commandants : télécharger les images manquantes AVANT
                    # d'écrire le JSON et d'émettre data_changed — sinon l'UI rafraîchit
                    # avec un commandant sans image alors que le fichier n'est pas encore là.
                    # On est déjà dans un thread worker, le blocage est acceptable.
                    if resource == "commanders":
                        self._pull_commander_images(server_data)

                    local_path.write_text(
                        json.dumps(server_data, indent=2, ensure_ascii=False),
                        encoding="utf-8",
                    )
                    changed = True
                except Exception:
                    pass

        if changed:
            # Signal cross-thread : Qt le met en file pour le thread principal
            self.data_changed.emit()

    def _pull_commander_images(self, commanders: list) -> None:
        """Télécharge depuis le serveur les images de commandants absentes localement."""
        try:
            from sync.server_client import _load_config
        except ImportError:
            return
        cfg = _load_config()
        if not cfg:
            return

        import urllib.request
        base_url = cfg["url"].rstrip("/")
        img_dir  = self._data_dir / "commander_images"
        img_dir.mkdir(parents=True, exist_ok=True)

        for commander in commanders:
            image_path = commander.get("image_path", "")
            if not image_path:
                continue
            local_file = self._data_dir / image_path
            if local_file.exists():
                continue  # Déjà présente localement
            filename = local_file.name
            url = f"{base_url}/commander_images/{filename}"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "MagicTable/1.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    local_file.write_bytes(resp.read())
            except Exception:
                pass  # Image indisponible → la carte s'affiche sans image
