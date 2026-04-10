"""
Client HTTP pour l'API MagicTable sur le serveur distant.

Configuration via src/data/server.json :
  { "url": "http://192.168.1.113:8000", "api_key": "magictable_secret_2026" }

Si le fichier est absent ou que le serveur est inaccessible, toutes les
opérations échouent silencieusement (retournent None) et l'app continue
avec ses fichiers locaux.
"""

import sys
import json
import threading
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional


def _get_config_path() -> Path:
    if getattr(sys, "frozen", False):
        if sys.platform == "win32":
            import os
            return Path(os.environ.get("APPDATA", "~")) / "MagicTable" / "data" / "server.json"
        return Path(sys.executable).parent / "data" / "server.json"
    # Développement : src/data/server.json
    return Path(__file__).parent.parent / "data" / "server.json"


_CONFIG_PATH = _get_config_path()

_config: Optional[dict] = None
_config_loaded = False


def _load_config() -> Optional[dict]:
    global _config, _config_loaded
    if _config_loaded:
        return _config
    _config_loaded = True
    if not _CONFIG_PATH.exists():
        return None
    try:
        _config = json.loads(_CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        _config = None
    return _config


def is_configured() -> bool:
    cfg = _load_config()
    return cfg is not None and bool(cfg.get("url"))


def fetch(resource: str) -> Optional[list]:
    """GET /{resource} → list ou None si échec."""
    cfg = _load_config()
    if not cfg:
        return None
    url = f"{cfg['url'].rstrip('/')}/{resource}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def push(resource: str, data: list) -> bool:
    """PUT /{resource} avec data en JSON. Retourne True si succès."""
    cfg = _load_config()
    if not cfg:
        return False
    url = f"{cfg['url'].rstrip('/')}/{resource}"
    api_key = cfg.get("api_key", "")
    try:
        body = json.dumps(data, ensure_ascii=False).encode()
        req = urllib.request.Request(url, data=body, method="PUT")
        req.add_header("Content-Type", "application/json")
        req.add_header("x-api-key", api_key)
        with urllib.request.urlopen(req, timeout=5):
            return True
    except Exception:
        return False


def push_async(resource: str, data: list) -> None:
    """Envoie data vers le serveur dans un thread (non-bloquant)."""
    threading.Thread(target=push, args=(resource, data), daemon=True).start()


def push_image(local_file: Path) -> bool:
    """Upload un fichier image vers le serveur. Retourne True si succès."""
    cfg = _load_config()
    if not cfg:
        return False
    if not local_file.exists():
        return False
    filename = local_file.name
    url = f"{cfg['url'].rstrip('/')}/upload/commander_images/{filename}"
    api_key = cfg.get("api_key", "")
    try:
        data = local_file.read_bytes()
        req = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/octet-stream")
        req.add_header("x-api-key", api_key)
        with urllib.request.urlopen(req, timeout=30):
            return True
    except Exception:
        return False


def push_commander_images_async(local_data_dir: Path, commanders: list) -> None:
    """Pousse toutes les images référencées dans commanders vers le serveur (non-bloquant)."""
    def _push_all():
        for commander in commanders:
            image_path = commander.get("image_path", "")
            if not image_path:
                continue
            push_image(local_data_dir / image_path)

    threading.Thread(target=_push_all, daemon=True).start()


def notify_start(tournament_id: str) -> bool:
    """Notifie l'API qu'un tournoi vient de démarrer (1er round créé)."""
    cfg = _load_config()
    if not cfg:
        return False
    url = f"{cfg['url'].rstrip('/')}/tournament/start"
    api_key = cfg.get("api_key", "")
    try:
        body = json.dumps({"tournament_id": tournament_id}, ensure_ascii=False).encode()
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("x-api-key", api_key)
        with urllib.request.urlopen(req, timeout=5):
            return True
    except Exception:
        return False


def notify_start_async(tournament_id: str) -> None:
    """Envoie la notification de démarrage dans un thread (non-bloquant)."""
    threading.Thread(target=notify_start, args=(tournament_id,), daemon=True).start()


def notify_quit(tournament_id) -> bool:
    """Notifie l'API que l'utilisateur a quitté le tournoi (suppression canaux)."""
    cfg = _load_config()
    if not cfg:
        return False
    url = f"{cfg['url'].rstrip('/')}/tournament/quit"
    api_key = cfg.get("api_key", "")
    try:
        body = json.dumps({"tournament_id": tournament_id}, ensure_ascii=False).encode()
        req = urllib.request.Request(url, data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("x-api-key", api_key)
        with urllib.request.urlopen(req, timeout=5):
            return True
    except Exception:
        return False


def notify_quit_async(tournament_id) -> None:
    """Envoie la notification de quitter dans un thread (non-bloquant)."""
    threading.Thread(target=notify_quit, args=(tournament_id,), daemon=True).start()


def pull_all(local_data_dir: Path) -> bool:
    """
    Télécharge tous les JSON depuis le serveur et les écrit localement.
    Télécharge aussi les images des commandants manquantes.
    Retourne True si au moins un fichier a été récupéré.
    """
    RESOURCES = {
        "players":     "regular_players.json",
        "tournaments": "tournaments.json",
        "leagues":     "leagues.json",
        "commanders":  "commanders.json",
    }
    if not is_configured():
        return False

    ok = False
    commanders_data = None
    for resource, filename in RESOURCES.items():
        data = fetch(resource)
        if data is not None:
            path = local_data_dir / filename
            path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            ok = True
            if resource == "commanders":
                commanders_data = data

    # Synchroniser les images des commandants manquantes
    if commanders_data:
        _pull_commander_images(local_data_dir, commanders_data)

    return ok


def _pull_commander_images(local_data_dir: Path, commanders: list) -> None:
    """Télécharge les images des commandants absentes localement."""
    cfg = _load_config()
    if not cfg:
        return
    base_url = cfg["url"].rstrip("/")
    img_dir = local_data_dir / "commander_images"
    img_dir.mkdir(parents=True, exist_ok=True)

    for commander in commanders:
        image_path = commander.get("image_path", "")
        if not image_path:
            continue
        local_file = local_data_dir / image_path
        if local_file.exists():
            continue  # Déjà présente

        # Télécharger depuis le serveur
        filename = Path(image_path).name
        url = f"{base_url}/commander_images/{filename}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "MagicTable/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                local_file.write_bytes(resp.read())
        except Exception:
            pass  # Image indisponible, la carte s'affichera sans image


# ── Notifications round vers le bot Discord ───────────────────────────────────

def _post_notify(endpoint: str, body: dict) -> bool:
    """POST vers /notify/<endpoint> avec authentification."""
    cfg = _load_config()
    if not cfg:
        return False
    url     = f"{cfg['url'].rstrip('/')}/notify/{endpoint}"
    api_key = cfg.get("api_key", "")
    try:
        data = json.dumps(body, ensure_ascii=False).encode()
        req  = urllib.request.Request(url, data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        req.add_header("x-api-key", api_key)
        with urllib.request.urlopen(req, timeout=8):
            return True
    except Exception:
        return False


def notify_round_start_async(
    tournament_id,
    round_num: "int | None",
    tournament_name: str,
    bracket_round: "str | None" = None,
) -> None:
    """Notifie le bot Discord que le chrono d'un round vient d'être lancé (non-bloquant)."""
    body = {
        "tournament_id":   tournament_id,
        "round_num":       round_num,
        "tournament_name": tournament_name,
        "bracket_round":   bracket_round,
    }
    threading.Thread(target=_post_notify, args=("round_start", body), daemon=True).start()


def notify_next_round_async(
    tournament_id,
    tournament_dict: dict,
    prev_round_num: "int | None" = None,
    prev_bracket_round: "str | None" = None,
    new_bracket_round: "str | None" = None,
    eliminated_names: "list | None" = None,
) -> None:
    """Notifie le bot du passage au round suivant : classement + pairings (non-bloquant)."""
    body = {
        "tournament_id":       tournament_id,
        "tournament_data":     tournament_dict,
        "prev_round_num":      prev_round_num,
        "prev_bracket_round":  prev_bracket_round,
        "new_bracket_round":   new_bracket_round,
        "eliminated_names":    eliminated_names or [],
    }
    threading.Thread(target=_post_notify, args=("next_round", body), daemon=True).start()
