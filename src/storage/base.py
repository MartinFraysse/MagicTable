import os
import sys
import json
from pathlib import Path
from json import JSONDecodeError


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
