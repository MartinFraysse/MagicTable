# src — MagicTable

Application desktop PySide6 qui gère des tournois de jeux de cartes : inscriptions, rondes (Swiss ou tables Commander), résultats, bracket, classements, statistiques.

## Stack

| Élément                  | Choix |
|--------------------------|-------|
| Langage et version       | Python 3.10+ (développé en 3.14) |
| Dépendances principales  | PySide6 (Qt 6) · networkx (appariement Swiss optimal) · certifi (HTTPS de la mise à jour) · fpdf2 (export PDF) |
| Gestion des dépendances  | pip + `requirements.txt` (venv `.venv/` à la racine) ; PyInstaller pour le `.exe` Windows |

## Organisation

```
src/
├── app.py          # point d'entrée : QApplication, thème, fenêtre principale
├── core/           # logique métier, sans Qt
│   ├── tournament.py      # entité centrale : joueurs, rondes, bracket, sérialisation
│   ├── swiss_pairing.py   # appariement Swiss (couplage de poids minimal)
│   ├── standings.py       # standings MTG : points, OMW%, GW%, OGW%
│   ├── ranking.py         # classement final (bracket prioritaire) + barème Commander
│   ├── bracket.py         # phase finale Top 2 / 4 / 8
│   ├── stats_analyzer.py  # stats joueurs (archives), tête-à-tête
│   ├── commander_stats.py # stats par commandant
│   ├── league.py          # ligues : classement cumulé
│   └── formats.py, player.py, round.py, table.py, regular_player.py, commander*.py, theme_manager.py
├── storage/        # persistance JSON (un fichier par ressource dans data/)
├── export/         # export PDF d'un tournoi
├── ui/             # interface : dashboard, tournois, joueurs, stats, ligues, commandants, paramètres
├── styles/         # thèmes QSS (sombre, clair)
├── assets/         # icônes, images des formats, sons
└── data/           # données utilisateur (en mode .exe : %APPDATA%\MagicTable\data)
```

Point d'entrée : `python src/app.py`

## Commandes

```bash
# installer les dépendances (depuis la racine)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# lancer
python src/app.py
# tester (pytest)
python -m pytest tests/ -q
# linter
python -m pyflakes src
# build Windows (.exe) — fait par la CI sur un tag v*
pyinstaller MagicTable.spec
```

## Configuration

Aucune variable d'environnement. Les données vivent dans `src/data/` (développement) ou
`%APPDATA%\MagicTable\data` (`.exe` Windows) ; les préférences (thème, timer) dans `data/config.json`.

## Conventions

- `core/` ne dépend jamais de Qt ni de `ui/` ; `storage/` ne dépend que de `core/`.
- Un seul point d'entrée par règle métier : classement final → `core.ranking.final_ranking`,
  formats → `core.formats`, création de ronde → `Tournament.create_round()`.
- Les tests vivent dans `tests/` (à la racine) et importent `src/` via `sys.path`.

## Idée d'ajout

<!-- Tenue par Claude : sections ou informations qui manquent à ce README.
     Une idée par puce : quoi ajouter → pourquoi. L'utilisateur approuve, puis l'idée est intégrée et retirée d'ici. -->
