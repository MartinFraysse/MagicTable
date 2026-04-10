import os
import sys
import json
from pathlib import Path
from json import JSONDecodeError

try:
    from sync.server_client import push_async
except ImportError:
    push_async = None  # type: ignore


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

    @classmethod
    def load(cls) -> list[dict]:
        path = cls._file()

        # Fichier inexistant
        if not path.exists():
            return []

        # Fichier vide
        if path.stat().st_size == 0:
            return []

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except JSONDecodeError:
            # JSON invalide / corrompu
            return []

    # Correspondance filename → resource API
    _RESOURCE_MAP: dict[str, str] = {
        "regular_players.json": "players",
        "tournaments.json":     "tournaments",
        "leagues.json":         "leagues",
        "commanders.json":      "commanders",
    }

    @classmethod
    def save(cls, data: list[dict]) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        with open(cls._file(), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # Push vers le serveur en arrière-plan (non-bloquant)
        resource = cls._RESOURCE_MAP.get(cls.filename)
        if resource and push_async is not None:
            push_async(resource, data)
