# MagicTable

## Overview

Application desktop de gestion de tournois **Magic: The Gathering**.
Permet d'organiser des tournois, gérer les joueurs, générer les tables automatiquement et suivre les scores en temps réel.

---

## Fonctionnalités

- Création et gestion de tournois (nom, format, date)
- Gestion des joueurs (ajout, suppression, renommage avec détection des doublons)
- Génération automatique des tables selon le format :
  - **Commander** : tables de 4 ou 3 joueurs (minimum 6 joueurs)
  - **Duel** : tables de 2 joueurs (minimum 4 joueurs)
- Système de rounds avec timer de 50 minutes
- Classement des joueurs par score et robustesse
- Interface drag & drop pour lancer les tournois
- Thème sombre vert personnalisé
- Persistance des données en JSON

---

## Structure du projet

```
src/
├── app.py                 # Point d'entrée de l'application
├── core/                  # Logique métier
│   ├── player.py          # Entité joueur
│   ├── tournament.py      # Entité tournoi + algorithmes
│   ├── round.py           # Gestion des rounds
│   └── table.py           # Entité table
├── storage/               # Persistance des données
│   ├── base.py            # Stockage JSON générique
│   └── tournaments.py     # Stockage des tournois
├── ui/                    # Interface utilisateur (PySide6)
│   ├── main_window.py     # Fenêtre principale
│   ├── dashboard/         # Vue tableau de bord
│   ├── tournaments/       # Gestion des tournois
│   └── widgets/           # Composants réutilisables
├── styles/                # Feuilles de style QSS
├── assets/                # Images et ressources
└── data/                  # Données persistées
    └── tournaments.json
```

---

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Langage | Python 3.14 |
| Framework UI | PySide6 (Qt for Python) |
| Persistance | JSON |
| Style | QSS (Qt Style Sheets) |
| OS | Linux (Arch) |

---

## Installation

### Prérequis

- Python 3.10+
- pip

### Installation des dépendances

```bash
cd src
python -m venv .venv
source .venv/bin/activate
pip install PySide6
```

---

## Lancement

```bash
cd src
python app.py
```

Ou depuis n'importe quel répertoire :

```bash
python /chemin/vers/MagicTable/src/app.py
```

---

## Utilisation

### Créer un tournoi

1. Aller dans l'onglet **Tournois**
2. Cliquer sur **Créer un tournoi**
3. Remplir le nom, format et date
4. Le tournoi apparaît dans la liste "À venir"

### Lancer un tournoi

1. Glisser-déposer une carte tournoi vers la zone de lancement
2. Ou clic droit → **Lancer**
3. Ajouter les joueurs dans la section de préparation
4. Cliquer sur **Démarrer le tournoi**

### Gérer les rounds

1. Les tables sont générées automatiquement
2. Le timer de 50 minutes démarre
3. Entrer les résultats de chaque table (clic droit → Modifier)
4. Cliquer sur **Round suivant** pour continuer

---

## Architecture

L'application suit une architecture en couches :

```
┌─────────────────────────────────────┐
│              UI Layer               │
│  (PySide6 Views, Widgets, Dialogs)  │
├─────────────────────────────────────┤
│           Storage Layer             │
│      (JSON File Persistence)        │
├─────────────────────────────────────┤
│            Core Layer               │
│   (Tournament, Player, Round, Table)│
└─────────────────────────────────────┘
```

**Patterns utilisés :**
- Signal/Slot (Qt) pour la communication entre composants
- Dataclasses pour les entités
- State Machine pour les états des rounds
- Factory Pattern pour la création de tournois

---

## Formats supportés

| Format | Joueurs/table | Min. joueurs |
|--------|---------------|--------------|
| Commander | 3-4 | 6 |
| Duel | 2 | 4 |

---

## Développement

### Configuration VS Code

Le projet inclut des tâches VS Code préconfigurées (`.vscode/tasks.json`) :

| Tâche | Description | Raccourci |
|-------|-------------|-----------|
| **Open Dev Terminal** | Ouvre un terminal avec nvm configuré | Auto à l'ouverture du projet |
| **Claude Code** | Lance Claude Code dans un nouveau terminal | `Ctrl+Shift+P` → "Run Task" |

> **Note** : Ces tâches utilisent nvm installé via pacman sur Arch Linux (`/usr/share/nvm/init-nvm.sh`). Sur d'autres systèmes, adapter le chemin vers `~/.nvm/nvm.sh`.

---

## Licence

Non spécifiée.
