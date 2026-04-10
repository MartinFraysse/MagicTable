"""
API FastAPI pour MagicTable — expose les données JSON du bot.
Démarrage : uvicorn api:app --host 0.0.0.0 --port 8000
"""

import json
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import APIKeyHeader

# ── Configuration ─────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).parent / "data"
PENDING_FILE = DATA_DIR / "pending_starts.json"

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


def _read(resource: str) -> list:
    path = DATA_DIR / f"{resource}.json"
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []


def _write(resource: str, data: Any) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{resource}.json"
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# ── Ressources JSON ───────────────────────────────────────────────────────────

@app.get("/players")
def get_players():
    return _read("players")


@app.put("/players")
def put_players(data: list, _: str = Depends(verify_key)):
    _write("players", data)
    return {"ok": True}


@app.get("/tournaments")
def get_tournaments():
    return _read("tournaments")


@app.put("/tournaments")
def put_tournaments(data: list, _: str = Depends(verify_key)):
    _write("tournaments", data)
    return {"ok": True}


@app.get("/leagues")
def get_leagues():
    return _read("leagues")


@app.put("/leagues")
def put_leagues(data: list, _: str = Depends(verify_key)):
    _write("leagues", data)
    return {"ok": True}


@app.get("/commanders")
def get_commanders():
    return _read("commanders")


@app.put("/commanders")
def put_commanders(data: list, _: str = Depends(verify_key)):
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
