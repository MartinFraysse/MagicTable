import json
from pathlib import Path
from json import JSONDecodeError


DATA_DIR = Path(__file__).parent.parent / "data"


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

    @classmethod
    def save(cls, data: list[dict]) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        with open(cls._file(), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
