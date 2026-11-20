# Commandes

> Les commandes pour lancer, tester, vérifier et construire MagicTable, et celles du projet.

Toutes se lancent **depuis la racine du dépôt**, environnement virtuel activé (`source .venv/bin/activate`).

## Application

| Commande | Effet |
|---|---|
| `pip install -r requirements.txt` | installe ou met à jour les dépendances (PySide6, networkx, fpdf2, certifi, pyinstaller) |
| `python src/app.py` | lance l'application |

## Qualité

| Commande | Effet |
|---|---|
| `pip install pytest pyflakes` | outils de développement (une fois) |
| `python -m pytest tests/ -q` | lance les tests |
| `python -m pyflakes src` | signale imports inutilisés, noms indéfinis, variables mortes |

Les tests :

| Fichier | Couvre |
|---|---|
| `tests/test_standings.py` | points, MW%, OMW%, byes, tri des standings |
| `tests/test_swiss.py` | priorités du Swiss, ronde 1 aléatoire, qualité et vitesse sur tournois simulés |
| `tests/test_core_rules.py` | bracket à effectif réduit, historique des byes, statistiques des joueurs réguliers |

## Build

| Commande | Effet |
|---|---|
| `pyinstaller MagicTable.spec` | construit l'exécutable dans `dist/` (sur Windows : `dist/MagicTable.exe`) |
| `git tag v1.6.7 && git push origin v1.6.7` | déclenche la CI : build Windows et release GitHub (voir le chapitre Exploitation) |

## Projet

| Commande | Où | Effet |
|---|---|---|
| `project MagicTable` | partout | ouvre le projet (Code, Claude, terminal) |
| `project site MagicTable` | partout | ouvre le site de suivi |
| `genpdf` | racine | génère le PDF de cette documentation : `docs/pdf/MagicTable.pdf` |
| `init-git` / `remove-git` | racine | crée ou supprime le dépôt GitHub |
