"""
API FastAPI pour MagicTable — expose les données JSON du bot.
Démarrage : uvicorn api:app --host 0.0.0.0 --port 8000
"""

import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Depends, Request, Body
from fastapi.security import APIKeyHeader

# ── Configuration ─────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent / "data"
PENDING_FILE          = DATA_DIR / "pending_starts.json"
PENDING_ROUND_STARTS  = DATA_DIR / "pending_round_starts.json"
PENDING_NEXT_ROUNDS   = DATA_DIR / "pending_next_rounds.json"
PENDING_QUITS         = DATA_DIR / "pending_quits.json"
PENDING_FINISHES      = DATA_DIR / "pending_finishes.json"

API_KEY = os.getenv("API_KEY", "magictable_secret_2026")
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

app = FastAPI(title="MagicTable API")

# ── Auth ───────────────────────────────────────────────────────────────────────

async def verify_key(key: str = Depends(api_key_header)):
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="Forbidden")
    return key


# ── Helpers ───────────────────────────────────────────────────────────────────

RESOURCES = ["players", "tournaments", "leagues", "commanders"]

FILENAMES = {
    "players":     "regular_players.json",
    "tournaments": "tournaments.json",
    "leagues":     "leagues.json",
    "commanders":  "commanders.json",
}


def _read(resource: str) -> list:
    path = DATA_DIR / FILENAMES.get(resource, f"{resource}.json")
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def _write(resource: str, data: Any) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / FILENAMES.get(resource, f"{resource}.json")
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Ressources JSON ───────────────────────────────────────────────────────────

@app.get("/players")
def get_players():
    return _read("players")


@app.put("/players")
def put_players(data: list = Body(...), _: str = Depends(verify_key)):
    # Fusionner les discord_id déjà présents côté serveur dans les données entrantes.
    # Empêche que le client (qui peut ignorer les !register récents) ne les écrase.
    existing = _read("players")
    if existing:
        server_discord = {
            str(p["id"]): p["discord_id"]
            for p in existing
            if p.get("discord_id")
        }
        # Construire aussi la map discord_pseudo côté serveur
        server_discord_pseudo = {
            str(p["id"]): p.get("discord_pseudo", "")
            for p in existing
            if p.get("discord_id")
        }
        for player in data:
            pid = str(player.get("id", ""))
            # Ne fusionner que si discord_id est ABSENT du payload (vieux client).
            # Si présent mais vide (""), c'est une déliaison intentionnelle → on la respecte.
            if pid in server_discord and "discord_id" not in player:
                player["discord_id"] = server_discord[pid]
                if not player.get("discord_pseudo") and pid in server_discord_pseudo:
                    player["discord_pseudo"] = server_discord_pseudo[pid]
    _write("players", data)
    # Retourner les données fusionnées pour que le client mette à jour son fichier local
    return data


@app.get("/tournaments")
def get_tournaments():
    return _read("tournaments")


@app.put("/tournaments")
def put_tournaments(data: list = Body(...), _: str = Depends(verify_key)):
    _write("tournaments", data)
    return {"ok": True}


@app.get("/leagues")
def get_leagues():
    return _read("leagues")


@app.put("/leagues")
def put_leagues(data: list = Body(...), _: str = Depends(verify_key)):
    _write("leagues", data)
    return {"ok": True}


@app.get("/commanders")
def get_commanders():
    return _read("commanders")


@app.put("/commanders")
def put_commanders(data: list = Body(...), _: str = Depends(verify_key)):
    _write("commanders", data)
    return {"ok": True}


# ── Notification démarrage tournoi ────────────────────────────────────────────

class TournamentStartPayload:
    pass


@app.post("/tournament/start")
async def tournament_start(request: Request, _: str = Depends(verify_key)):
    """
    Reçu quand MagicTable lance le 1er round d'un tournoi.
    Ajoute l'ID dans pending_starts.json pour que le bot le prenne en charge.
    """
    body = await request.json()
    tournament_id = body.get("tournament_id", "")
    if not tournament_id:
        raise HTTPException(status_code=400, detail="tournament_id requis")

    # Lire la file existante
    if PENDING_FILE.exists():
        try:
            pending = json.loads(PENDING_FILE.read_text(encoding="utf-8"))
        except Exception:
            pending = []
    else:
        pending = []

    if tournament_id not in pending:
        pending.append(tournament_id)
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        PENDING_FILE.write_text(json.dumps(pending, indent=2), encoding="utf-8")

    return {"ok": True, "tournament_id": tournament_id}


def _append_pending(path: Path, item) -> None:
    """Ajoute un élément à une liste pending JSON (crée le fichier si besoin)."""
    if path.exists():
        try:
            items = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            items = []
    else:
        items = []
    items.append(item)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")


@app.post("/notify/round_start")
async def notify_round_start(request: Request, _: str = Depends(verify_key)):
    """Notifié quand le chrono d'un round est lancé."""
    body = await request.json()
    _append_pending(PENDING_ROUND_STARTS, body)
    return {"ok": True}


@app.post("/notify/next_round")
async def notify_next_round(request: Request, _: str = Depends(verify_key)):
    """Notifié quand on passe au round suivant (Swiss ou bracket)."""
    body = await request.json()
    _append_pending(PENDING_NEXT_ROUNDS, body)
    return {"ok": True}


@app.post("/notify/finish")
async def notify_finish(request: Request, _: str = Depends(verify_key)):
    """Notifié quand un tournoi est terminé — classement final."""
    body = await request.json()
    _append_pending(PENDING_FINISHES, body)
    return {"ok": True}


@app.post("/tournament/quit")
async def tournament_quit(request: Request, _: str = Depends(verify_key)):
    """Notifié quand l'utilisateur quitte le dashboard — suppression des canaux."""
    body = await request.json()
    tournament_id = body.get("tournament_id", "")
    if not tournament_id:
        raise HTTPException(status_code=400, detail="tournament_id requis")
    _append_pending(PENDING_QUITS, tournament_id)
    return {"ok": True}
