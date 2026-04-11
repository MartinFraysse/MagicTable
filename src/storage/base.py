import os
import sys
import json
from pathlib import Path
from json import JSONDecodeError

try:
    from sync.server_client import fetch, is_configured, push_async, push_commander_images_async
except ImportError:
    fetch = None                         # type: ignore
    is_configured = lambda: False        # type: ignore
    push_async = None                    # type: ignore
    push_commander_images_async = None   # type: ignore


def _resolve_data_dir() -> Path:
    """
    Retourne le répertoire des données utilisateur.
    - Mode packagé (PyInstaller .exe) : %APPDATA%\\MagicTable\\data
    - Mode développement              : src/data  (comportement historique)
    """
    if getattr(sys, "frozen", False):
        if sys.platform == "win32":
            # Windows packagé : %APPDATA%\MagicTable\data
            data_dir = Path(os.environ.get("APPDATA", "~")) / "MagicTable" / "data"
        else:
            # Linux packagé : à côté du binaire
            data_dir = Path(sys.executable).parent / "data"
    else:
        data_dir = Path(__file__).parent.parent / "data"

    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


DATA_DIR = _resolve_data_dir()


class JsonStorage:
    filename: str  # à définir dans les subclasses

    @classmethod
    def _file(cls) -> Path:
        return DATA_DIR / cls.filename

    # Correspondance filename → resource API
    _RESOURCE_MAP: dict[str, str] = {
        "regular_players.json": "players",
        "tournaments.json":     "tournaments",
        "leagues.json":         "leagues",
        "commanders.json":      "commanders",
    }

    @classmethod
    def load(cls) -> list[dict]:
        resource = cls._RESOURCE_MAP.get(cls.filename)

        # ── Lecture depuis le serveur (source de vérité) ──────────────────────
        if resource and fetch is not None and is_configured():
            data = fetch(resource, timeout=2)
            if data is not None:
                # Mettre en cache localement (fallback offline)
                try:
                    path = cls._file()
                    path.write_text(
                        json.dumps(data, indent=2, ensure_ascii=False),
                        encoding="utf-8",
                    )
                except Exception:
                    pass
                return data

        # ── Fallback : fichier local ──────────────────────────────────────────
        path = cls._file()
        if not path.exists() or path.stat().st_size == 0:
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except JSONDecodeError:
            return []

    @classmethod
    def save(cls, data: list[dict]) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        with open(cls._file(), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Push vers le serveur en arrière-plan (non-bloquant)
        resource = cls._RESOURCE_MAP.get(cls.filename)
        if resource and push_async is not None:
            push_async(resource, data)
            # Pour les commandants : synchroniser aussi les images
            if resource == "commanders" and push_commander_images_async is not None:
                push_commander_images_async(DATA_DIR, data)
