# MagicTable

Application desktop de gestion de tournois de jeux de cartes (Magic: The Gathering, Duel Commander, Pokémon…).

---

## Fonctionnalités

### Tournois
- Création de tournois avec nom, format, date et nombre de rounds
- 6 formats supportés : Commander, Duel Commander, Draft, AP, Pokémon, Rise
- Deux systèmes d'appariement : **Standard** (score + robustesse) et **Swiss officiel MTG**
- Glisser-déposer pour charger un tournoi en zone de lancement
- Timer de round configurable (par défaut 50 minutes)
- Fenêtre de projection plein écran pour afficher les tables

### Rounds & Résultats
- Génération automatique des tables selon le format et l'effectif
- Saisie des résultats par double-clic ou menu contextuel sur une carte table
- Support **BO3 (Best of 3)** pour les formats 1v1 (5 résultats : 2-0, 2-1, 1-1, 1-2, 0-2)
- Détection des répétitions de tables + bouton "Round varié" pour les éviter
- Modification manuelle des pairings au round 1

### Standings MTG officiels
- Calcul complet : **MW%**, **OMW%**, **GW%**, **OGW%**
- Plancher OMW% à 33% (règle officielle)
- Tri officiel : Match Points → OMW% → GW% → OGW% → Nom

### Swiss
- Appariement par bracket de score avec backtracking
- Bye automatique pour effectif impair (rotation équitable)
- **Rematches impossibles** : si tous les appariements possibles ont déjà eu lieu, la génération du round est bloquée avec un message d'erreur
- Départages Buchholz et SOS calculés automatiquement

### Phase de bracket d'élimination
Disponible après le dernier round Swiss pour les formats 1v1 :
- **Top 2** — Finale directe
- **Top 4** — Demi-finales + Finale
- **Top 8** — Quarts + Demi-finales + Finale

Les seeds sont issus du classement final des rounds Swiss. Les gagnants progressent automatiquement vers le match suivant.

### Joueurs réguliers
- Registre permanent de joueurs (pseudo, nom complet, téléphone)
- Autocomplétion lors de l'inscription à un tournoi
- Cumul inter-tournois : points, podiums (top 1/2/3), tournois joués

### Statistiques
- Stats globales : distribution des formats, commandants populaires
- Classement des joueurs réguliers par points
- Tête-à-tête : historique des confrontations entre deux joueurs

### Export & thèmes
- Export **PDF** du classement final et des détails de rounds (nécessite `fpdf2`)
- Deux thèmes : **Dark** et **Light** (vert)

---

## Installation

### Prérequis

- Python 3.10+
- PySide6

```bash
cd src
python -m venv .venv
source .venv/bin/activate
pip install PySide6

# Optionnel : export PDF
pip install fpdf2
```

### Lancement

```bash
cd src
python app.py
```

---

## Utilisation rapide

### Créer et lancer un tournoi

1. Onglet **Tournois** → **Créer un tournoi** → remplir nom, format, date, nombre de rounds
2. La carte apparaît dans "À venir" — la glisser vers la zone de lancement (ou clic droit → Lancer)
3. Ajouter les joueurs (saisie manuelle ou autocomplétion depuis les joueurs réguliers)
4. Cliquer sur **🚀 Lancer le tournoi**

> Le bouton reste désactivé tant que l'effectif minimum n'est pas atteint :
> **6 joueurs** pour Commander, **4 joueurs** pour les autres formats.

### Gérer les rounds

1. **▶ Lancer le round** — démarre le timer
2. Double-cliquer sur une carte table pour entrer les résultats
3. Quand toutes les tables sont terminées → **⏭ Round suivant** (ou **🏁 Terminer le tournoi** au dernier round)
4. En mode Swiss, si tous les joueurs se sont déjà affrontés, la création du round est bloquée avec un message d'erreur

### Lancer un bracket d'élimination

Après le dernier round Swiss :
1. Cliquer sur **🏆 Lancer le bracket**
2. Choisir le format (Top 2 / Top 4 / Top 8)
3. Entrer les résultats de chaque match (double-clic sur la carte)
4. **⏭ Phase suivante** pour avancer vers les demi-finales puis la finale

### Archiver un tournoi

Une fois le tournoi terminé, cliquer sur **📦 Archiver le tournoi** — il apparaît dans l'onglet Historique.
Les résultats des joueurs réguliers (points, podiums) sont enregistrés automatiquement.

---

## Structure du projet

```
MagicTable/
├── src/
│   ├── app.py                  ← Point d'entrée
│   ├── core/                   ← Logique métier (sans Qt)
│   │   ├── player.py
│   │   ├── regular_player.py
│   │   ├── tournament.py       ← Entité centrale + algorithmes
│   │   ├── round.py
│   │   ├── table.py
│   │   ├── bracket.py          ← Bracket d'élimination
│   │   ├── standings.py        ← Standings MTG officiels
│   │   ├── swiss_pairing.py    ← Appariement Swiss
│   │   ├── stats_analyzer.py
│   │   └── theme_manager.py
│   ├── storage/                ← Persistance JSON
│   │   ├── base.py
│   │   ├── tournaments.py
│   │   └── regular_players.py
│   ├── export/
│   │   └── pdf_export.py
│   ├── ui/                     ← Interface PySide6
│   │   ├── main_window.py
│   │   ├── dashboard/
│   │   ├── tournaments/
│   │   ├── players/
│   │   ├── stats/
│   │   └── settings_view.py
│   ├── styles/                 ← Thèmes QSS
│   └── data/                   ← Données (JSON, auto-créé)
│       ├── tournaments.json
│       ├── regular_players.json
│       └── config.json
├── tests/
│   └── test_standings.py
├── docs/                       ← Documentation interne
├── TECHNICAL_DOC.md            ← Documentation technique détaillée
└── README.md
```

---

## Formats supportés

| Format | Tables | Effectif min. | Pairing | Scoring |
|--------|--------|---------------|---------|---------|
| 👑 Commander | 3-4 joueurs | 6 | Standard | Position : 1er=3pts, 2e=2pts, 3e-4e=1pt |
| ⚔️ Duel Commander | 2 joueurs | 4 | Swiss | V=3pts, N=1pt, D=0pt |
| 🃏 Draft | 2 joueurs | 4 | Swiss | V=3pts, N=1pt, D=0pt |
| AP | 2 joueurs | 4 | Swiss | V=3pts, N=1pt, D=0pt |
| 🎮 Pokémon | 2 joueurs | 4 | Swiss | V=3pts, N=1pt, D=0pt |
| ⚡ Rise | 2 joueurs | 4 | Swiss | V=3pts, N=1pt, D=0pt |

---

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Langage | Python 3.10+ |
| Framework UI | PySide6 (Qt 6) |
| Persistance | JSON |
| Style | QSS (Qt Style Sheets) |
| Export PDF | fpdf2 (optionnel) |
| Tests | pytest |
| OS | Linux (développé sur Arch) |

---

## Tests

```bash
cd /path/to/MagicTable
PYTHONPATH=src python -m pytest tests/ -v
```

Les tests couvrent le calcul des standings MTG officiels (`core/standings.py`).

---

## Documentation technique

Pour les détails d'architecture, les algorithmes, les dataclasses, les signaux Qt et le format JSON : voir **[TECHNICAL_DOC.md](TECHNICAL_DOC.md)**.

---

## Développement

### Configuration VS Code

Le projet inclut des tâches préconfigurées (`.vscode/tasks.json`) :

| Tâche | Description |
|-------|-------------|
| **Open Dev Terminal** | Terminal avec nvm configuré |
| **Claude Code** | Lance Claude Code dans un terminal dédié |

> Ces tâches utilisent nvm installé via pacman (`/usr/share/nvm/init-nvm.sh`). Adapter le chemin sur d'autres distributions.

---

## Licence

Projet personnel — aucune licence open source définie.
