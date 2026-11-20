# MagicTable

Application desktop de gestion de tournois de jeux de cartes (Magic: The Gathering, Duel Commander, Pokémon…).

## Commandes

| Commande | Où la lancer | Effet |
|---|---|---|
| `project MagicTable` | partout (ou `Super + P`) | Ouvre le projet : Code, Claude, un terminal |
| `project site MagicTable` | partout | Ouvre le site de suivi : ce que Claude propose et a fait |
| `genpdf` | à la racine du projet | Génère le PDF de la doc : `docs/pdf/MagicTable.pdf` |
| `init-git` | à la racine du projet | Crée le dépôt git et le dépôt GitHub privé, et pousse |
| `remove-git` | à la racine du projet | Supprime le dépôt GitHub et le `.git` local (les fichiers restent) |
| `project remove MagicTable` | partout | Supprime le projet (propose aussi le dépôt GitHub) |

Détails : `INIT.md`.

## Fonctionnalités

### Tournois
- Création de tournois avec nom, format, date et nombre de rounds
- 6 formats supportés : Commander, Duel Commander, Draft, AP, Pokémon, Rise
- Appariement automatique selon le format : **Swiss** pour tous les formats 1v1 (Duel Commander, Draft, AP, Pokémon, Rise), tables de 3-4 (score + robustesse) pour le **Commander multi**
- Glisser-déposer pour charger un tournoi en zone de lancement
- Timer de round configurable (par défaut 50 minutes)
- Fenêtre de projection plein écran pour afficher les tables

### Rounds & Résultats
- Génération automatique des tables selon le format et l'effectif
- Saisie des résultats par double-clic ou menu contextuel sur une carte table
- Support **BO3 (Best of 3)** pour les formats 1v1 (5 résultats : 2-0, 2-1, 1-1, 1-2, 0-2)
- Commander multi : détection des répétitions de tables + bouton "Round varié" pour les éviter
- Modification manuelle des pairings au round 1

### Standings MTG officiels
- Calcul complet : **MW%**, **OMW%**, **GW%**, **OGW%**
- Plancher OMW% à 33% (règle officielle)
- Tri officiel : Match Points → OMW% → GW% → OGW% → Nom

### Swiss
- Appariement **optimal** à chaque round (couplage de poids minimal, quelques millisecondes même à 40+ joueurs). Priorités :
  1. pas de second bye tant qu'un autre joueur peut le recevoir
  2. pas de revanche si une alternative existe (sinon, le minimum de revanches)
  3. bye au joueur ayant le moins de points
  4. adversaires les plus proches en points (on évite les gros écarts, ex. 9 pts contre 0 pt)
  5. tirage au sort entre joueurs équivalents — le round 1 est entièrement aléatoire
- Bye = victoire 2-0 (3 points, compte dans le GW%), conformément à la MTR

### Phase de bracket d'élimination
Disponible après le dernier round Swiss pour les formats 1v1 :
- **Top 2** — Finale directe
- **Top 4** — Demi-finales + Finale
- **Top 8** — Quarts + Demi-finales + Finale

Les seeds sont issus du classement final des rounds Swiss. Les gagnants progressent automatiquement vers le match suivant.
S'il manque des joueurs (effectif réduit ou abandons), un joueur sans adversaire passe au tour suivant ; il ne gagne jamais un match dont l'adversaire n'est pas encore connu.

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

## Formats supportés

| Format | Tables | Effectif min. | Pairing | Scoring |
|--------|--------|---------------|---------|---------|
| 👑 Commander | 3-4 joueurs | 6 | Tables 3-4 | Position : 1er=3pts, 2e=2pts, 3e-4e=1pt |
| ⚔️ Duel Commander | 2 joueurs | 4 | Swiss | V=3pts, N=1pt, D=0pt |
| 🃏 Draft | 2 joueurs | 4 | Swiss | V=3pts, N=1pt, D=0pt |
| AP | 2 joueurs | 4 | Swiss | V=3pts, N=1pt, D=0pt |
| 🎮 Pokémon | 2 joueurs | 4 | Swiss | V=3pts, N=1pt, D=0pt |
| ⚡ Rise | 2 joueurs | 4 | Swiss | V=3pts, N=1pt, D=0pt |

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # PySide6, networkx, fpdf2, certifi, pyinstaller
```

### Lancement

```bash
python src/app.py
```

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
4. En Swiss, une revanche n'est générée que si aucune autre combinaison n'est possible

### Lancer un bracket d'élimination

Après le dernier round Swiss :
1. Cliquer sur **🏆 Lancer le bracket**
2. Choisir le format (Top 2 / Top 4 / Top 8)
3. Entrer les résultats de chaque match (double-clic sur la carte)
4. **⏭ Phase suivante** pour avancer vers les demi-finales puis la finale

### Archiver un tournoi

Une fois le tournoi terminé, cliquer sur **📦 Archiver le tournoi** — il apparaît dans l'onglet Historique.
Les statistiques des joueurs réguliers (points, podiums, tournois joués) sont recalculées à partir des tournois archivés.

## Tests

```bash
cd /path/to/MagicTable
PYTHONPATH=src python -m pytest tests/ -v
```

Les tests couvrent les standings MTG (`test_standings.py`), l'appariement Swiss (`test_swiss.py`),
le bracket, les byes et les stats des joueurs réguliers (`test_core_rules.py`).

## Organisation du dépôt

```
.
├── .claude/
│   ├── CLAUDE.md          # consignes de Claude Code (principes, qui écrit quoi, journal)
│   ├── regles-doc.md      # règles de la doc : notes, plan, procédure « rédige la doc »
│   ├── regles-site.md     # règles du site de suivi (docs/site/)
│   ├── hooks/
│   │   └── journal.sh     # donne le journal à Claude (résumé au démarrage seulement)
│   ├── SESSION_LOG.md     # journal des sessions (mémoire entre sessions)
│   └── settings.json      # hook SessionStart : lance hooks/journal.sh
├── .github/workflows/
│   └── build.yml          # build Windows (.exe) et release GitHub sur un tag v*
├── docs/
│   ├── .claude_doc.md     # plan de la doc et notes de Claude (hors PDF)
│   ├── 01-presentation/   # présentation, glossaire
│   ├── 02-guides/         # installation, organiser un tournoi, joueurs et statistiques
│   ├── 03-architecture/   # fonctionnement, appariements et classements, decisions/ (ADR)
│   ├── 04-reference/      # formats et barème, données JSON, commandes
│   ├── 05-exploitation/   # build et mises à jour, dépannage
│   ├── pdf/               # page de garde et PDF de la doc (genpdf)
│   ├── site/              # site de suivi : propositions et réalisations de Claude (project site MagicTable)
│   └── README.md          # règles de la documentation
├── src/
│   ├── app.py             # point d'entrée de l'application
│   ├── core/              # logique métier, sans Qt (tournoi, Swiss, standings, bracket, classements, stats)
│   ├── storage/           # persistance JSON
│   ├── export/            # export PDF
│   ├── ui/                # interface PySide6
│   ├── styles/            # thèmes QSS
│   ├── assets/            # icônes, images des formats, sons
│   ├── data/              # données de l'application (JSON, images des commandants)
│   ├── updater.py         # mise à jour automatique depuis les releases GitHub
│   ├── version.py         # numéro de version
│   └── README.md          # stack, organisation et commandes du code
├── tests/                 # tests pytest (standings, Swiss, bracket, stats)
├── .editorconfig          # style commun à tous les éditeurs
├── .env.example           # variables d'environnement attendues, sans valeurs
├── .gitignore             # fichiers exclus de git (secrets, dépendances, builds)
├── .vscode/               # tâches VS Code (terminal, Claude Code)
├── CHANGELOG.md           # historique des versions
├── GIT.md                 # aide-mémoire des commandes git du projet
├── INIT.md                # aide-mémoire : créer, ouvrir, publier et supprimer un projet
├── MagicTable.spec        # configuration PyInstaller (build du .exe)
├── requirements.txt       # dépendances Python
└── README.md
```

Les fichiers de la racine s'appliquent à tout le dépôt ; le code vit dans `src/`, la documentation dans `docs/`.
Documentation complète : `docs/` (chapitres `01` à `05`), exportée en PDF dans `docs/pdf/MagicTable.pdf` par `genpdf`.

## Stratégie de branches : trunk-based development

- `main` est la **seule branche permanente**. Elle doit toujours rester stable.
- Tout travail se fait sur une **branche courte** (quelques heures, 2 jours maximum), créée depuis `main`.
- Une branche courte revient dans `main` **uniquement via une Pull Request**.
- Exception : les branches de release figées (`release/<version>`), qui ne reçoivent que des correctifs par cherry-pick.

## Convention de nommage des branches

Format : `<type>/<description>`

| Type       | Usage                                           | Exemple                   |
|------------|-------------------------------------------------|---------------------------|
| `feat`     | Nouvelle fonctionnalité                         | `feat/page-connexion`     |
| `fix`      | Correction de bug                               | `fix/crash-au-demarrage`  |
| `docs`     | Documentation uniquement                        | `docs/guide-contribution` |
| `chore`    | Maintenance, configuration, outillage           | `chore/update-gitignore`  |
| `refactor` | Restructuration sans changement de comportement | `refactor/module-auth`    |
| `test`     | Ajout ou correction de tests                    | `test/api-utilisateurs`   |
| `ci`       | Pipeline d'intégration continue                 | `ci/github-actions`       |

Règles : minuscules, mots séparés par des tirets, pas d'espaces ni d'accents.

Les messages de commit suivent le même vocabulaire ([Conventional Commits](https://www.conventionalcommits.org/fr/)) :
`<type>(<scope>): <description>` — par exemple `feat(auth): ajoute la connexion`.

## Règle de merge

- **Aucun push direct sur `main`** : uniquement des Pull Request.
- La PR doit être à jour avec `main` et passer les vérifications avant d'être fusionnée.
- Mode de merge : **Squash and merge**.
- La branche est **supprimée après le merge**.

## Workflow type

```bash
git switch main && git pull              # partir d'un main à jour
git switch -c feat/ma-fonctionnalite     # créer une branche courte
# ... travailler, committer ...
git push -u origin feat/ma-fonctionnalite
# ouvrir la Pull Request sur GitHub, puis Squash and merge
git switch main && git pull              # récupérer le résultat
git branch -D feat/ma-fonctionnalite     # nettoyer la branche locale (-D : le squash crée un nouveau commit)
```

## Licence

Projet personnel — aucune licence open source définie.
