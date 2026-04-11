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

INTERVAL_MS = 30_000  # 30 secondes

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
