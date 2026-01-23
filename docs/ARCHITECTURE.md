# MagicTable - Documentation Technique

Application de gestion de tournois Magic: The Gathering développée avec PySide6 (Qt pour Python).

---

## Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Structure du projet](#structure-du-projet)
3. [Couche Core (Métier)](#couche-core-métier)
4. [Couche Storage (Persistance)](#couche-storage-persistance)
5. [Couche UI (Interface)](#couche-ui-interface)
6. [Styles et Thème](#styles-et-thème)
7. [Flux de données](#flux-de-données)
8. [Algorithmes clés](#algorithmes-clés)

---

## Vue d'ensemble

### Fonctionnalités principales

- Création et gestion de tournois (Commander, Duel, Draft)
- Génération automatique des tables optimales
- Suivi des scores et classements en temps réel
- Timer de 50 minutes par round
- Système de robustesse pour départager les égalités
- Historique des tournois archivés

### Stack technique

| Composant | Technologie |
|-----------|-------------|
| Langage | Python 3.x |
| Framework UI | PySide6 (Qt6) |
| Persistance | JSON |
| Styling | QSS (Qt Style Sheets) |

### Architecture

```
┌──────────────────────────────────────────┐
│            UI Layer (PySide6)            │
│  MainWindow → QStackedWidget (5 vues)    │
├──────────────────────────────────────────┤
│           Storage Layer                  │
│      (Persistance JSON fichiers)         │
├──────────────────────────────────────────┤
│            Core Layer                    │
│   Tournament → Player, Round → Table     │
│      (Logique métier, algorithmes)       │
└──────────────────────────────────────────┘
```

---

## Structure du projet

```
src/
├── app.py                    # Point d'entrée de l'application
├── core/                     # Logique métier (modèles de domaine)
│   ├── player.py             # Entité joueur
│   ├── table.py              # Entité table
│   ├── round.py              # Entité round
│   └── tournament.py         # Orchestration tournoi
├── storage/                  # Persistance des données
│   ├── base.py               # Classe abstraite JsonStorage
│   └── tournaments.py        # Stockage des tournois
├── ui/                       # Interface utilisateur
│   ├── main_window.py        # Fenêtre principale
│   ├── dashboard/            # Vue dashboard (round en cours)
│   ├── tournaments/          # Gestion des tournois
│   └── widgets/              # Composants réutilisables
├── styles/                   # Fichiers QSS (thème)
├── assets/                   # Images et icônes
└── data/                     # Données persistées (JSON)
```

---

## Couche Core (Métier)

### `core/player.py`

Représente un joueur dans le tournoi.

```python
@dataclass
class Player:
    id: int              # Identifiant unique
    name: str            # Nom du joueur
    score: int = 0       # Points accumulés
    robustness: int = 0  # Force des adversaires affrontés
```

**Méthodes:**
- `add_score(points)` : Ajoute des points au score
- `add_robustness(value)` : Ajoute à la robustesse

---

### `core/table.py`

Représente une table de jeu (groupe de joueurs pour un match).

```python
@dataclass
class Table:
    number: int                      # Numéro de table
    players: list[Player]            # Joueurs assignés
    finished: bool = False           # Match terminé ?
    results: dict[int, int] = {}     # {player_id: position}
```

**Propriétés:**
- `player_count` : Nombre de joueurs à la table (3 ou 4 en Commander)

---

### `core/round.py`

Représente un round (phase) du tournoi.

```python
class RoundState(Enum):
    PREPARATION = "preparation"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"

@dataclass
class Round:
    number: int              # Numéro du round
    tables: list[Table]      # Tables de ce round
    state: RoundState        # État actuel
```

**Machine à états:**
```
PREPARATION → IN_PROGRESS → FINISHED
    │              │            │
  start()       (timer)     finish()
```

---

### `core/tournament.py`

Classe principale orchestrant toute la logique métier.

```python
@dataclass
class Tournament:
    id: int
    name: str
    format: str           # "👑 Commander", "⚔️ Duel", etc.
    date: str             # Format "DD/MM/YYYY"
    players: list[Player]
    rounds: list[Round]
    max_rounds: int = 3
    archived: bool = False
```

**Méthodes principales:**

| Méthode | Description |
|---------|-------------|
| `add_player(name)` | Ajoute un joueur (vérifie doublons) |
| `remove_player(id)` | Supprime un joueur |
| `create_round()` | Génère un nouveau round avec tables |
| `sort_players()` | Trie par score puis robustesse |
| `compute_table_sizes(n)` | Calcule la répartition optimale |
| `recalculate_robustness()` | Recalcule la robustesse de tous |
| `get_opponents_map()` | Retourne les adversaires déjà rencontrés |
| `create_round_by_opponents()` | Round en évitant les répétitions |
| `reset()` | Réinitialise scores et rounds |
| `archive()` | Archive le tournoi terminé |

---

## Couche Storage (Persistance)

### `storage/base.py`

Classe abstraite pour la persistance JSON.

```python
DATA_DIR = Path(__file__).parent.parent / "data"

class JsonStorage:
    filename: str  # Défini dans les sous-classes

    @classmethod
    def load(cls) -> list[dict]:
        # Charge le fichier JSON, gère les erreurs

    @classmethod
    def save(cls, data: list[dict]) -> None:
        # Sauvegarde avec création du dossier si nécessaire
```

### `storage/tournaments.py`

```python
class TournamentStorage(JsonStorage):
    filename = "tournaments.json"
```

**Format de données:**
```json
[
  {
    "id": 1,
    "name": "Tournoi du vendredi",
    "format": "👑 Commander",
    "date": "24/01/2025",
    "max_rounds": 3,
    "archived": false,
    "players": [
      {"id": 0, "name": "Alice", "score": 6, "robustness": 24}
    ],
    "rounds": [...]
  }
]
```

---

## Couche UI (Interface)

### `app.py` - Point d'entrée

```python
def main():
    app = QApplication(sys.argv)
    # Charge tous les fichiers QSS
    # Crée MainWindow
    # Lance la boucle événementielle
```

### `ui/main_window.py`

Fenêtre principale avec navigation par sidebar.

```
┌─────────┬────────────────────────────┐
│ Sidebar │      Content Area          │
│         │    (QStackedWidget)        │
│ 🏠 Home │                            │
│ 🏆 Tour │   Vue active (1 sur 5)     │
│ 👥 Play │                            │
│ 🎮 Match│                            │
│ ⚙️ Sett │                            │
└─────────┴────────────────────────────┘
```

**5 vues empilées:**
1. Dashboard (round en cours)
2. Tournaments (gestion)
3. Players (à venir)
4. Matches (à venir)
5. Settings (à venir)

---

### `ui/dashboard/` - Dashboard

Le dashboard est l'écran principal pendant un tournoi actif.

#### `dashboard_view_main.py`

Orchestrateur du dashboard, gère:
- Tiles d'information (6 tuiles)
- Vue classement (8 joueurs visibles)
- Vue tables (scroll horizontal)
- Contrôles de round

**Signaux émis:**
- `tournament_changed` : Déclenche une sauvegarde
- `tournament_archived` : Notifie l'archivage

#### `tiles_view.py`

6 tuiles d'information:
- État actif
- Nom du tournoi
- Nombre de joueurs
- Nombre de tables
- Round actuel / max
- Timer (50:00)

#### `ranking_view.py`

Tableau de classement avec:
- Position (#)
- Nom du joueur
- Score (coloré selon évolution)
- Popup au survol (historique + robustesse)

#### `tables_view.py`

Affichage horizontal des tables avec:
- Numéro de table
- Cartes joueurs
- Bouton "Résultats" pour saisir les positions

#### `round_controls_view.py`

Boutons de contrôle:
- ▶️ Démarrer le round
- ➡️ Round suivant
- 🔀 Round varié (évite répétitions)
- 🔄 Réinitialiser
- 📦 Archiver

#### `dialogs/edit_table_results.py`

Dialog pour saisir les résultats:
- Dropdown pour chaque joueur (1er, 2ème, 3ème, 4ème)
- Calcul automatique des points

---

### `ui/tournaments/` - Gestion des tournois

#### `tournaments_view_main.py`

Page principale divisée en 3 zones:
```
┌──────────────────────────────────────┐
│  Upcoming (à venir)                  │
│  [Card] [Card] [+]                   │
├──────────────────────────────────────┤
│  Launch (espace de travail)          │
│  [Joueurs...] [Démarrer]             │
├──────────────────────────────────────┤
│  Historic (archivés)                 │
│  [Card] [Card]                       │
└──────────────────────────────────────┘
```

#### `upcoming_view.py`

Liste des tournois à lancer:
- Cartes draggables
- Menu contextuel (éditer, lancer, supprimer)
- Bouton "+" pour créer

#### `launch_view.py`

Zone de préparation:
- Drop zone pour tournoi
- Liste des joueurs (ajouter/éditer/supprimer)
- Bouton "Démarrer le tournoi"

#### `historic_view.py`

Tournois archivés (lecture seule).

---

### `ui/widgets/` - Composants réutilisables

| Widget | Usage |
|--------|-------|
| `TournamentCard` | Carte visuelle d'un tournoi |
| `HorizontalScrollArea` | Scroll horizontal pour tables |
| `DownOnlyComboBox` | Dropdown qui s'ouvre vers le bas |
| `PlayerMatchesPopup` | Tooltip historique joueur |

---

## Styles et Thème

7 fichiers QSS dans `styles/`:

| Fichier | Cible |
|---------|-------|
| `dark_green_main.qss` | Fenêtre principale, sidebar |
| `dark_green_dashboard.qss` | Dashboard (tiles, ranking, tables) |
| `dark_green_tournament.qss` | Gestion des tournois |
| `dark_green_widget.qss` | Widgets communs |
| `dark_green_player.qss` | Vue joueurs |
| `dark_green_matche.qss` | Vue matchs |
| `dark_green_setting.qss` | Vue paramètres |

**Palette de couleurs:**
- Background: `#1a1a2e` (bleu très foncé)
- Accent: `#16213e` (bleu foncé)
- Primary: `#0f3460` (bleu)
- Highlight: `#e94560` (rose/rouge)
- Text: `#ffffff` / `#aaaaaa`
- Success: `#3fd27d` (vert)
- Warning: `#f1c40f` (jaune)

---

## Flux de données

### Création d'un tournoi

```
CreateTournamentDialog
        │
        ▼
Tournament.create_tournament()
        │
        ▼
UpcomingView.add_tournament()
        │
        ▼
TournamentStorage.save()
        │
        ▼
tournaments.json
```

### Déroulement d'un round

```
User: Démarrer round
        │
        ▼
Tournament.create_round()
        │
        ├─► compute_table_sizes()
        │
        └─► _generate_tables() ou _generate_tables_by_opponents()
                    │
                    ▼
            DashboardViewMain.set_current_round()
                    │
                    ▼
            TablesView.set_round() + RankingView.set_tournament()
                    │
                    ▼
            User: Saisir résultats (EditTableResultsDialog)
                    │
                    ▼
            _apply_table_scores() → Player.add_score()
                    │
                    ▼
            Tournament.recalculate_robustness()
                    │
                    ▼
            tournament_changed.emit() → TournamentStorage.save()
```

---

## Algorithmes clés

### Calcul des tailles de tables

Pour le format Commander (tables de 3 ou 4):

```python
def compute_table_sizes(player_count):
    # Maximiser les tables de 4, compléter avec des 3
    # Exemple: 11 joueurs → [4, 4, 3]
    # Minimum: 6 joueurs
```

**Règle:** `4*a + 3*b = n` où on maximise `a`

### Système de points

| Position | Points |
|----------|--------|
| 1er | 3 pts |
| 2ème | 2 pts |
| 3ème | 1 pt |
| 4ème | 1 pt |

### Calcul de la robustesse

```python
def recalculate_robustness():
    N = len(players)
    for each finished_table:
        for each player:
            for each opponent:
                robustness += (N - opponent_current_rank)
```

**Caractéristiques:**
- Rétroactif (recalculé selon classement actuel)
- Plus l'adversaire est fort, plus ça rapporte
- Utilisé comme critère de départage

### Évitement des répétitions

```python
def _generate_tables_by_opponents():
    # Algorithme glouton:
    # 1. Pour chaque table à remplir
    # 2. Choisir le joueur avec le moins de conflits
    # 3. Conflit = adversaire déjà rencontré
    # 4. Bonus diversité robustesse (-0.01 * écart à la moyenne)
```

---

## Signals et Slots (Communication inter-vues)

| Signal | Émetteur | Récepteur | Action |
|--------|----------|-----------|--------|
| `tournament_changed` | DashboardViewMain | MainWindow | Sauvegarde |
| `tournament_archived` | DashboardViewMain | TournamentViewMain | Rafraîchir listes |
| `edit_results_requested` | TablesView | DashboardViewMain | Ouvrir dialog |
| `start_round_requested` | RoundControls | DashboardViewMain | Démarrer timer |
| `tournament_selected` | UpcomingView | LaunchView | Charger tournoi |

---

## Lancement de l'application

```bash
cd src/
python app.py
```

**Prérequis:**
- Python 3.x
- PySide6 (`pip install PySide6`)
