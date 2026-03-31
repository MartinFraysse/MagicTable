# MagicTable — Documentation Technique

## Sommaire

1. [Vue d'ensemble](#1-vue-densemble)
2. [Architecture générale](#2-architecture-générale)
3. [Couche Core](#3-couche-core)
   - [Player](#31-player)
   - [RegularPlayer](#32-regularplayer)
   - [Table](#33-table)
   - [Round](#34-round)
   - [Tournament](#35-tournament)
   - [Bracket](#36-bracket)
   - [Standings](#37-standings)
   - [Swiss Pairing](#38-swiss-pairing)
   - [Stats Analyzer](#39-stats-analyzer)
   - [Theme Manager](#310-theme-manager)
4. [Couche Storage](#4-couche-storage)
5. [Couche UI](#5-couche-ui)
   - [MainWindow](#51-mainwindow)
   - [Dashboard](#52-dashboard)
   - [Tournois](#53-tournois)
   - [Joueurs](#54-joueurs)
   - [Stats](#55-stats)
   - [Paramètres](#56-paramètres)
6. [Signaux et connexions](#6-signaux-et-connexions)
7. [Formats de tournoi](#7-formats-de-tournoi)
8. [Algorithmes clés](#8-algorithmes-clés)
9. [Sérialisation JSON](#9-sérialisation-json)
10. [Styles QSS](#10-styles-qss)
11. [Tests](#11-tests)
12. [Dépendances](#12-dépendances)

---

## 1. Vue d'ensemble

MagicTable est une application desktop Python/PySide6 (Qt6) pour la gestion de tournois de jeux de cartes (Magic: The Gathering, Pokémon, etc.).

**Fonctionnalités principales :**
- Création et gestion de tournois multi-formats
- Appariement automatique Standard et Swiss officiel MTG
- Calcul des standings officiels MTG (OMW%, GW%, OGW%)
- Phase de bracket d'élimination (Top 2 / Top 4 / Top 8)
- Classement des joueurs permanents inter-tournois
- Statistiques globales, tête-à-tête, historique
- Export PDF des résultats
- Fenêtre de projection plein écran
- Thèmes dark/light

**Stack :**
- Python 3.12+
- PySide6 (Qt 6)
- fpdf2 (export PDF, optionnel)

**Point d'entrée :** `src/app.py`
**Données :** `src/data/` (fichiers JSON)
**Styles :** `src/styles/` (fichiers QSS)

---

## 2. Architecture générale

```
src/
├── app.py                          ← Point d'entrée
├── core/                           ← Logique métier pure (pas de Qt)
│   ├── player.py
│   ├── regular_player.py
│   ├── table.py
│   ├── round.py
│   ├── tournament.py
│   ├── bracket.py
│   ├── standings.py
│   ├── swiss_pairing.py
│   ├── stats_analyzer.py
│   └── theme_manager.py
├── storage/                        ← Persistance JSON
│   ├── base.py
│   ├── tournaments.py
│   └── regular_players.py
├── export/
│   └── pdf_export.py
├── ui/                             ← Interface graphique Qt
│   ├── main_window.py
│   ├── dashboard/
│   ├── tournaments/
│   ├── players/
│   ├── stats/
│   ├── settings_view.py
│   └── widgets/
├── styles/                         ← Feuilles de style QSS
└── data/                           ← Données persistées (JSON)
    ├── tournaments.json
    ├── regular_players.json
    └── config.json
```

**Flux de données :**
```
JSON → Tournament.from_dict() → objets core → UI affiche
UI modifie → objets core mutés → tournament_changed signal → JSON sauvegardé
```

La couche `core` ne dépend jamais de Qt. Toute la logique métier y est testable de façon unitaire.

---

## 3. Couche Core

### 3.1 Player

**Fichier :** `src/core/player.py`

Représente un joueur **dans le cadre d'un tournoi**. Objet éphémère : il est créé à l'inscription au tournoi et disparaît avec lui.

```python
@dataclass
class Player:
    id: int                    # Identifiant unique dans le tournoi (auto-incrémenté)
    name: str                  # Nom du joueur
    score: int = 0             # Points de match accumulés (3 = victoire, 1 = nul, 0 = défaite)
    robustness: int = 0        # Départage Commander : somme pondérée des rangs adversaires
    reward_claimed: bool = False
    commander: str = ""        # Nom du deck (formats Commander uniquement)
    buchholz: float = 0.0      # Départage Swiss : somme des scores adversaires
    sos: float = 0.0           # Strength of Schedule : moyenne des scores adversaires
    had_bye: bool = False      # A déjà reçu un bye dans ce tournoi
```

**Méthodes :**
- `add_score(points: int)` — ajoute des points
- `add_robustness(value: int)` — ajoute à la robustesse

---

### 3.2 RegularPlayer

**Fichier :** `src/core/regular_player.py`

Représente un joueur **permanent** enregistré dans l'application. Persiste entre tous les tournois.

```python
@dataclass
class RegularPlayer:
    id: int
    pseudo: str
    full_name: str = ""
    phone: str = ""
    top_1: int = 0             # Nombre de premières places
    top_2: int = 0
    top_3: int = 0
    points: int = 0            # Points cumulés sur tous les tournois
    tournaments_played: int = 0
```

**Méthodes :**
- `add_top(position: int)` — incrémente `top_1`, `top_2` ou `top_3`
- `total_podiums` *(property)* — `top_1 + top_2 + top_3`

**Lien avec `Player` :** uniquement par correspondance de nom (insensible à la casse). Il n'y a pas de clé étrangère entre les deux modèles.

---

### 3.3 Table

**Fichier :** `src/core/table.py`

Représente une table de jeu à l'intérieur d'un round.

```python
@dataclass
class Table:
    number: int
    players: list[Player]
    finished: bool = False
    results: dict[int, int] = {}       # player_id → position (1er, 2e, 3e, 4e)
    game_scores: dict[int, int] = {}   # player_id → games gagnées (BO3)
```

**Table BYE :** une table avec un seul joueur (`len(players) == 1`). Elle est créée automatiquement avec `finished=True` et `results={player.id: 1}`.

**Sérialisation :** seuls les `player_id` sont stockés en JSON. Les objets `Player` sont reconstruits à partir d'un dictionnaire `players_by_id` lors du chargement.

---

### 3.4 Round

**Fichier :** `src/core/round.py`

```python
class RoundState(str, Enum):
    PREPARATION = "preparation"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"

@dataclass
class Round:
    number: int
    tables: list[Table] = []
    state: RoundState = RoundState.PREPARATION
```

---

### 3.5 Tournament

**Fichier :** `src/core/tournament.py`

Dataclass centrale contenant toute la logique métier d'un tournoi.

```python
@dataclass
class Tournament:
    id: int
    name: str
    format: str                        # "👑 Commander", "⚔️ Duel Commander", etc.
    date: str                          # "DD/MM/YYYY"
    players: list[Player] = []
    rounds: list[Round] = []
    max_rounds: int = 3
    archived: bool = False
    podiums_recorded: bool = False
    pairing_system: str = "standard"   # "standard" ou "swiss"
    bye_history: set[int] = set()      # IDs des joueurs ayant reçu un bye
    bracket: Bracket | None = None     # Phase d'élimination (optionnelle)
```

**Méthodes — gestion des joueurs :**

| Méthode | Description |
|---|---|
| `add_player(name)` | Ajoute un joueur (déduplique, insensible à la casse). Retourne `None` si doublon. |
| `remove_player(player_id)` | Supprime un joueur par ID. |
| `rename_player(player_id, new_name)` | Renomme. Retourne `False` si introuvable. |

**Méthodes — cycle de vie des rounds :**

| Méthode | Description |
|---|---|
| `create_round()` | Appariement Standard par score. Retourne `None` si impossible (effectif invalide). |
| `create_round_by_opponents()` | Appariement qui minimise les répétitions de tables. |
| `create_round_swiss()` | Appariement Swiss officiel. **Lève `ValueError`** si rematch inévitable. |
| `can_create_round()` | `True` si `len(rounds) < max_rounds` ET pas de bracket actif. |
| `is_finished()` | `True` si rounds complets et dernier round entièrement terminé. |
| `reset()` | Supprime tous les rounds, remet les scores à zéro, efface le bracket. |

**Méthodes — standings et départages :**

| Méthode | Description |
|---|---|
| `calculate_swiss_tiebreakers()` | Met à jour `player.buchholz` et `player.sos` pour tous les joueurs. |
| `sort_players()` | Tri par score desc, robustness desc (Standard/Commander). |
| `sort_players_swiss()` | Tri officiel Swiss : score → buchholz → sos → nom. |
| `recalculate_robustness()` | Recalcule la robustesse Commander après chaque round. |
| `get_opponents_map()` | `dict[player_id → set(opponent_ids)]` depuis tout l'historique. |
| `compute_repetition_rate(tables)` | Taux de répétitions pour un ensemble de tables proposées. |
| `would_have_repetitions()` | `(bool, taux)` pour le prochain round Standard. |

**Méthodes — bracket :**

| Méthode | Description |
|---|---|
| `start_bracket(bracket_type)` | Crée le bracket depuis le classement actuel, stocke dans `self.bracket`. |
| `is_bracket_phase` *(property)* | `True` si bracket non nul et non terminé. |

**Méthodes utilitaires :**

| Méthode | Description |
|---|---|
| `compute_table_sizes(n)` | Retourne la liste des tailles de tables optimales, ou `None`. |
| `table_count()` | Nombre de tables pour l'effectif actuel. |
| `is_swiss_format()` | `pairing_system == "swiss"` |
| `is_1v1_format()` | `format != "👑 Commander"` |
| `get_recommended_rounds()` | `ceil(log2(n))` — recommandation Swiss. |
| `player_count` *(property)* | Nombre de joueurs inscrits. |

---

### 3.6 Bracket

**Fichier :** `src/core/bracket.py`

Modèle de la phase d'élimination directe.

```python
class BracketType(str, Enum):
    FINAL = "final"              # Top 2 — 1 match
    DEMI_FINALE = "demi"         # Top 4 — 3 matches
    QUART_DE_FINALE = "quart"    # Top 8 — 7 matches

class BracketRoundName(str, Enum):
    QUART = "quart"
    DEMI = "demi"
    FINAL = "final"

@dataclass
class BracketMatch:
    match_id: int
    round_name: BracketRoundName
    position: int               # Index 0-based dans le round
    player1_id: int | None      # None tant que le joueur n'est pas qualifié
    player2_id: int | None
    winner_id: int | None
    finished: bool = False
    next_match_id: int | None   # Match où le gagnant progresse

@dataclass
class Bracket:
    bracket_type: BracketType
    matches: list[BracketMatch] = []
    finished: bool = False
```

**Structure des matchs par type :**

| Type | Matches | Pairings initiaux |
|---|---|---|
| `FINAL` | 1 (ID 0) | 1er vs 2e |
| `DEMI_FINALE` | 3 (IDs 0-2) | 1v4, 2v3 → Finale |
| `QUART_DE_FINALE` | 7 (IDs 0-6) | 1v8, 4v5, 2v7, 3v6 → Demis → Finale |

**Méthodes de `Bracket` :**

| Méthode | Description |
|---|---|
| `current_round_name()` | Premier round dont tous les matches ne sont pas terminés. `None` si bracket fini. |
| `get_matches_for_round(round_name)` | Filtre les matches par round. |
| `all_current_round_finished()` | `True` si tous les matches du round actif sont terminés. |
| `record_result(match_id, winner_id)` | Enregistre le résultat et propage le gagnant au match suivant. Met `finished=True` sur le bracket si la Finale est jouée. |
| `get_round_order()` | Liste ordonnée des rounds selon le `bracket_type`. |

**Fonction factory :**
```python
create_bracket_matches(bracket_type, seeded_player_ids) -> list[BracketMatch]
```
Construit les matches initiaux à partir d'une liste d'IDs classés (seed 1 = meilleur classement).

---

### 3.7 Standings

**Fichier :** `src/core/standings.py`

```python
build_standings(tournament: Tournament) -> list[StandingEntry]
```

Implémentation du **système de standings officiels MTG Swiss** en 5 phases.

**`StandingEntry` (dataclass) :**
```python
player_id: int
player_name: str
match_points: int      # 3 × victoires + 1 × nuls
wins: int
draws: int
losses: int
matches_played: int
mw_pct: float          # Match Win % = match_points / (3 × matches_played)
omw_pct: float         # Opponent Match Win %
gw_pct: float          # Game Win % (BO3 uniquement, sinon 0.0)
ogw_pct: float         # Opponent Game Win %
```

**Phase 1 — Collecte des résultats bruts**

Pour chaque round terminé et chaque table finie :
- **Bye** (1 joueur, `finished=True`) → victoire, pas d'adversaire enregistré.
- **1v1** (2 joueurs) : position 1 = vainqueur, position 3 = perdant, égalité = nul.
  - Si `game_scores` présents, accumule `games_won` et `games_played`.
- Les tables non terminées ou aux résultats incomplets sont ignorées silencieusement.

**Phase 2 — MW% (Match Win %)**
```
mw_pct = match_points / (3 × matches_played)
```
Vaut `0.0` si aucun match joué.

**Phase 3 — OMW% (Opponent Match Win %)**
```
omw_pct(J) = moyenne( max(adv.mw_pct, 0.33) pour chaque adversaire de J )
```
Le plancher de **0.33** (règle officielle MTG) empêche qu'un adversaire à 0% pénalise excessivement le calcul. Vaut `0.0` si aucun adversaire.

**Phase 4 — GW% et OGW%**
```
gw_pct = games_won / games_played   (si scores BO3 enregistrés, sinon 0.0)
ogw_pct = moyenne( max(adv.gw_pct, 0.33) pour chaque adversaire )
```

**Phase 5 — Tri**
```
clé = (-match_points, -omw_pct, -gw_pct, -ogw_pct, nom_joueur)
```

---

### 3.8 Swiss Pairing

**Fichier :** `src/core/swiss_pairing.py`

```python
generate_swiss_pairings(
    players: list[Player],
    opponents_map: dict[int, set[int]],
    bye_history: set[int],
    standings_order: list[int] | None = None,
) -> SwissPairingResult
```

```python
@dataclass
class SwissPairingResult:
    pairings: list[tuple[Player, Player]]
    bye_player: Player | None
    rematch_forced: bool = False   # True si des rematches étaient inévitables
```

**Algorithme en 4 étapes :**

**Étape 1 — Attribution du bye (effectif impair)**
- Parcourt le classement du dernier au premier.
- Sélectionne le premier joueur sans bye précédent (`id not in bye_history`).
- Si tous ont eu un bye : le dernier du classement le reçoit à nouveau.
- Le joueur bye est retiré du pool actif.

**Étape 2 — Groupement par bracket de score**
```python
score_brackets: dict[int, list[Player]]
```
Les joueurs sont groupés par `player.score`. L'ordre de traitement est décroissant (meilleurs scores d'abord).

**Étape 3 — Appariement par bracket**
- Les "floaters" (joueurs non appariés du bracket précédent) sont fusionnés avec le bracket suivant.
- `_pair_bracket()` est appelé sur chaque groupe fusionné.
- Les joueurs restants non appariés deviennent floaters pour le bracket inférieur.

**`_pair_bracket(players, opponents_map)` — backtracking :**

Minimise le nombre de floaters en évitant tous les rematches (paires où les deux joueurs se sont déjà affrontés) :
1. Sélectionne le premier joueur disponible.
2. Tente tous ses partenaires valides (jamais rencontrés).
3. Si aucun partenaire valide : le joueur devient floater.
4. Élagage : abandonne les branches ne pouvant pas améliorer la meilleure solution connue.
5. Arrêt anticipé si une solution sans floater est trouvée.

**Étape 4 — Floaters résiduels**
- Si des joueurs restent non appariés après tous les brackets : ils sont forcés en paires (rematches inévitables).
- `rematch_forced = True` est positionné sur le résultat.
- `create_round_swiss()` dans `Tournament` **lève une `ValueError`** si ce cas se produit.

**Fonction utilitaire :**
```python
compute_recommended_rounds(n: int) -> int   # ceil(log2(n))
```

---

### 3.9 Stats Analyzer

**Fichier :** `src/core/stats_analyzer.py`

Lit les tournois archivés et calcule des statistiques agrégées. Utilisé uniquement par les vues de stats et la vue joueurs réguliers.

Méthodes principales :
- `get_global_stats()` — nombre total de tournois, joueurs uniques, format le plus joué, commander le plus populaire.
- `get_player_rankings()` — classement des joueurs réguliers par points.
- `get_head_to_head(player_a_id, player_b_id)` — historique des confrontations directes.
- `get_format_distribution()` — répartition par format.

---

### 3.10 Theme Manager

**Fichier :** `src/core/theme_manager.py`

Singleton qui gère la préférence de thème (dark/light).

```python
ThemeManager()       # Retourne toujours la même instance
```

- **Stockage :** `src/data/config.json` → `{"theme": "dark" | "light"}`
- **Défaut :** `"dark"` si config absente ou corrompue.
- **`set_app(app: QApplication)`** — à appeler une fois au démarrage pour activer le changement de thème à chaud.
- **`set_theme(theme: str)`** — met à jour, sauvegarde et applique le stylesheet.
- **`load_theme_stylesheet()`** — concatène les 7 fichiers QSS du thème actif.

> **Note :** Dans `app.py` actuel, les styles sont chargés directement sans passer par `ThemeManager.set_app()`. Le changement de thème à chaud n'est donc pas encore câblé.

---

## 4. Couche Storage

**Fichier base :** `src/storage/base.py`

```python
class JsonStorage:
    filename: str    # À définir dans les sous-classes

    @classmethod
    def load(cls) -> list[dict]

    @classmethod
    def save(cls, data: list[dict]) -> None
```

- Dossier de données : `src/data/` (créé automatiquement si absent).
- `load()` retourne `[]` en cas de fichier absent, vide ou JSON invalide (jamais d'exception).
- `save()` écrit avec `indent=2, ensure_ascii=False`.

**Sous-classes :**

| Classe | Fichier | Contenu |
|---|---|---|
| `TournamentStorage` | `tournaments.json` | Tous les tournois (actifs + archivés) |
| `RegularPlayerStorage` | `regular_players.json` | Joueurs permanents |

**Déclencheurs de sauvegarde des tournois :**

Le signal `DashboardViewMain.tournament_changed` est émis lors de toutes les opérations mutatrices :
- Création d'un round (Standard, Swiss, Bracket)
- Saisie d'un résultat de table ou de match bracket
- Archivage du tournoi
- Ajout / suppression / renommage d'un joueur
- Réinitialisation

`MainWindow` connecte ce signal à `TournamentViewMain.save_tournaments()` qui appelle `TournamentStorage.save()`.

**Déclencheurs de sauvegarde des joueurs réguliers :**
- CRUD depuis `PlayersViewMain`
- "Ajouter aux joueurs réguliers" depuis le menu contextuel du classement
- `_record_podiums()` à la fin du tournoi

---

## 5. Couche UI

### 5.1 MainWindow

**Fichier :** `src/ui/main_window.py`

Fenêtre principale (1380 × 920 px minimum).

**Structure :**
```
QHBoxLayout
├── Sidebar (260 px fixe)            ← 5 boutons de navigation + logo
└── QStackedWidget                   ← 5 vues empilées
    ├── [0] DashboardViewMain
    ├── [1] TournamentViewMain
    ├── [2] PlayersViewMain
    ├── [3] StatsViewMain
    └── [4] SettingsView
```

**Comportement :**
- Clic sur un bouton de nav → `stack.setCurrentIndex(i)`.
- Navigation vers "Joueurs" (index 2) → `players_view.refresh()`.
- Navigation vers "Stats" (index 3) → `stats_view.refresh()`.
- `start_tournament(tournament)` → bascule sur le Dashboard (index 0), transmet la durée du timer depuis les paramètres.

---

### 5.2 Dashboard

**Fichier principal :** `src/ui/dashboard/dashboard_view_main.py`

Orchestrateur de la vue de tournoi actif.

**Layout vertical :**
```
QVBoxLayout
├── DashboardTilesView     ← KPI (tournoi actif, nom, joueurs, tables, round, timer)
├── DashboardRankingView   ← Classement en temps réel
├── DashboardTablesView    ← Cartes de tables (rounds Swiss) ou de matches (bracket)
└── DashboardRoundControlsView ← Boutons de contrôle
```

**État interne :**
```python
current_tournament: Tournament | None
current_round: Round | None
_bracket_mode: bool                     # True si en phase bracket
_bracket_displayed_round: BracketRoundName | None
timer_duration: int                     # Minutes (depuis les paramètres)
```

**Cycle de vie d'un round Standard/Swiss :**
1. `set_current_round(tournament)` — initialise l'affichage pour le round courant.
2. `_start_round()` — démarre le timer Qt (1 s).
3. `_edit_table_results(table)` → `EditTableResultsDialog` → mise à jour scores.
4. Quand toutes les tables sont terminées → `set_next_enabled(True)`.
5. `_next_round()` — crée le round suivant ou termine le tournoi.

**Cycle de vie du bracket :**
1. Après le dernier round Swiss → bouton "🏆 Lancer le bracket" apparaît.
2. `_launch_bracket()` — `QInputDialog` pour choisir le format → `tournament.start_bracket()` → `_setup_bracket_mode()`.
3. `_edit_bracket_result(match)` → `EditBracketResultDialog` → `bracket.record_result()`.
4. Quand tous les matches du round sont terminés → `set_next_enabled(True)`.
5. `_advance_bracket_round()` — passe au round suivant ou termine.
6. Au dernier round (Finale terminée) → `_finish_tournament()`.

**Composants du dashboard :**

| Composant | Fichier | Rôle |
|---|---|---|
| `DashboardTilesView` | `tiles_view.py` | 6 tuiles KPI |
| `DashboardRankingView` | `ranking_view.py` | Tableau de classement (3 modes) |
| `DashboardTablesView` | `tables_view.py` | Cartes de tables/matches |
| `DashboardRoundControlsView` | `round_controls_view.py` | Boutons d'action |
| `PairingsWindow` | `pairings_window.py` | Fenêtre de projection détachée |
| `FinalStandingsOverlay` | `final_standings_overlay.py` | Overlay de fin de tournoi |

**Modes d'affichage du classement (`DashboardRankingView`) :**

| Mode | Colonnes | Activé quand |
|---|---|---|
| Commander | #, Joueur, Score, Robustesse | `format == "👑 Commander"` |
| Swiss 1v1 | #, Joueur, Score, OMW%, GW%, W-L-D | `is_swiss_format()` et `is_1v1_format()` |
| Standard 1v1 | #, Joueur, Score | Autre |

**Dialogs :**

| Dialog | Fichier | Déclencheur |
|---|---|---|
| `EditTableResultsDialog` | `edit_table_results.py` | Double-clic sur une carte de table |
| `EditBracketResultDialog` | `edit_bracket_result.py` | Double-clic sur une carte de match bracket |
| `EditPairingsDialog` | `edit_pairings_dialog.py` | Bouton "Modifier les pairings" (round 1 uniquement) |
| `RoundSummaryDialog` | `round_summary_dialog.py` | Menu contextuel du classement |

**`DashboardRoundControlsView` — boutons et états :**

| Bouton | Objet QSS | Visible quand |
|---|---|---|
| ▶ Lancer le round | `PrimaryButton` | Toujours (en mode normal) |
| ⏭ Round suivante / 🏁 Terminer | `SecondaryButton` / `FinishButton` | Toujours |
| ✏️ Modifier les pairings | `SecondaryButton` | Round 1, avant tout résultat |
| 🔀 Round varié | `WarningButton` | Mode Standard, si répétitions détectées |
| 🏆 Lancer le bracket | `BracketButton` | Dernier round Swiss terminé (1v1 ≥ 4 joueurs) |
| 📦 Archiver | `ArchiveButton` | Tournoi terminé |
| 📄 Exporter PDF | `SecondaryButton` | Tournoi terminé |
| ⏭ Phase suivante | `SecondaryButton` | Mode bracket |

---

### 5.3 Tournois

**Fichier principal :** `src/ui/tournaments/tournaments_view_main.py`

Conteneur avec 3 sous-vues :

**`UpcomingView`** — Liste des tournois non archivés sous forme de cartes `TournamentCard`.
- Drag-and-drop : les cartes peuvent être glissées vers `LaunchView`.
- CRUD complet (créer, éditer, supprimer).
- Signal `launch_requested(Tournament)`.

**`LaunchView`** — Panneau de préparation d'un tournoi.
- Accepte les tournois par drag-and-drop depuis `UpcomingView`.
- Liste de joueurs avec autocomplétion sur les joueurs réguliers.
- Menu contextuel joueur : éditer, supprimer, ajouter aux réguliers, set commander.
- Validation : bouton "Lancer" désactivé si effectif insuffisant + label d'avertissement.
  - Commander : minimum 6 joueurs.
  - Autres formats : minimum 4 joueurs.
- Signal `start_requested(Tournament)` → `MainWindow.start_tournament()`.

**`HistoricView`** — Galerie des tournois archivés.
- Double-clic → `TournamentDetailDialog` (classement final, par round).
- Export PDF depuis `RewardsDialog`.
- Suppression avec confirmation.

---

### 5.4 Joueurs

**Fichier :** `src/ui/players/players_view_main.py`

Tableau CRUD pour les `RegularPlayer`.
- Colonnes : Pseudo, Nom, Top 1/2/3, Points, Tournois joués.
- Menu contextuel : éditer, supprimer, voir les stats détaillées.
- Les points sont issus de `StatsAnalyzer` (calculés depuis les tournois archivés).

---

### 5.5 Stats

**Fichier :** `src/ui/stats/stats_view_main.py`

3 onglets :

| Onglet | Vue | Contenu |
|---|---|---|
| Stats globales | `GlobalStatsView` | KPI, distribution formats, commandants populaires |
| Classements | `RankingsView` | Tableau des joueurs réguliers par points |
| Tête-à-tête | `HeadToHeadView` | Sélecteur de 2 joueurs + historique des confrontations |

`refresh()` est appelé à chaque navigation vers l'onglet Stats.

---

### 5.6 Paramètres

**Fichier :** `src/ui/settings_view.py`

- Durée du timer (spinbox, en minutes) — propagée au Dashboard via `timer_duration_changed(int)`.
- Référentiel du système de scoring (lecture seule).
- Gestion des données :
  - "Supprimer les tournois archivés"
  - "Supprimer tous les tournois"
  - "Supprimer tous les joueurs"
- Signal `tournaments_cleared()` → `MainWindow._on_tournaments_cleared()`.

---

## 6. Signaux et connexions

### Flux principal

```
TournamentCard (drag)
    → LaunchView (drop)
        → [start_requested]
            → TournamentViewMain._start_tournament()
                → [round_started]
                    → MainWindow.start_tournament()
                        → DashboardViewMain.set_current_round()
```

```
DashboardTablesView.edit_results_requested
    → DashboardViewMain._edit_table_results()
        → tournament mutated
            → [tournament_changed]
                → TournamentViewMain.save_tournaments()
                    → TournamentStorage.save()
```

```
DashboardRoundControlsView.next_round_requested
    → DashboardViewMain._next_round()
        → tournament.create_round_swiss()  (ou create_round / bracket)
            → DashboardViewMain.set_current_round()
                → [tournament_changed]
```

```
DashboardRoundControlsView.archive_requested
    → DashboardViewMain._archive_tournament()
        → tournament.archive()
            → [tournament_archived(id)]
                → TournamentViewMain.on_tournament_archived()
                → TournamentStorage.save()
```

### Tableau récapitulatif des signaux custom

| Émetteur | Signal | Paramètre | Récepteur |
|---|---|---|---|
| `DashboardViewMain` | `tournament_changed` | — | `TournamentViewMain.save_tournaments` |
| `DashboardViewMain` | `tournament_archived` | `int` (id) | `TournamentViewMain.on_tournament_archived` |
| `TournamentViewMain` | `round_started` | `Tournament` | `MainWindow.start_tournament` |
| `LaunchView` | `start_requested` | `Tournament` | `TournamentViewMain._start_tournament` |
| `LaunchView` | `tournament_taken` | `int` | `UpcomingView.hide_tournament_card` |
| `LaunchView` | `tournament_cancelled` | `int` | `UpcomingView.show_tournament_card` |
| `LaunchView` | `edit_requested` | `Tournament` | `TournamentViewMain._edit_from_launch` |
| `UpcomingView` | `launch_requested` | `Tournament` | `TournamentViewMain._launch_from_card` |
| `DashboardRankingView` | `player_added_to_regulars` | `str` | `LaunchView.refresh_regular_players` |
| `HistoricView` | `tournament_deleted` | `int` | `TournamentViewMain._on_historic_tournament_deleted` |
| `SettingsView` | `timer_duration_changed` | `int` | `MainWindow` (forward au Dashboard) |
| `SettingsView` | `tournaments_cleared` | — | `MainWindow._on_tournaments_cleared` |

---

## 7. Formats de tournoi

| Format | Tables | Système de score | Pairing par défaut |
|---|---|---|---|
| 👑 Commander | 3-4 joueurs | Position : 1er=3pts, 2e=2pts, 3e-4e=1pt | Standard (score + robustesse) |
| ⚔️ Duel Commander | 2 joueurs | Match Win : W=3pts, D=1pt, L=0 | Swiss |
| 🃏 Draft | 2 joueurs | Match Win | Swiss |
| AP | 2 joueurs | Match Win | Swiss |
| 🎮 Pokemon | 2 joueurs | Match Win | Swiss |
| ⚡ Rise | 2 joueurs | Match Win | Swiss |

**Effectif minimum :**
- Commander : **6 joueurs** (au moins 2 tables de 3)
- Autres formats : **4 joueurs** (au moins 2 tables de 2)

**Calcul des tailles de tables (Commander) :**
- Priorité aux tables de 3 si l'effectif est divisible par 3.
- Sinon, recherche de la meilleure combinaison (tables de 4 + tables de 3).
- Retourne `None` si impossible (< 6 joueurs ou combinaison invalide).

**BO3 (Best of 3) :**
- Disponible pour tous les formats 1v1 via `EditTableResultsDialog`.
- 5 boutons radio : 2-0, 2-1, 1-1, 1-2, 0-2.
- `Table.game_scores` stocke les games gagnées par joueur.
- GW% et OGW% sont calculés dans les standings si `game_scores` présents.

---

## 8. Algorithmes clés

### Appariement Commander (Standard)

Utilisé pour les formats multiplayer (`pairing_system = "standard"` et `format == "👑 Commander"`).

**`Tournament.create_round()` :**
1. Trie les joueurs par score décroissant, puis robustesse décroissante.
2. Calcule les tailles de tables (`compute_table_sizes`).
3. Distribue les joueurs triés dans les tables dans l'ordre.

**`Tournament.create_round_by_opponents()` :**
Algorithme glouton qui minimise les répétitions de tables :
1. Calcule un score de conflit pour chaque joueur candidat à chaque table.
2. Score de conflit = nombre d'adversaires déjà rencontrés à cette table.
3. Bonus de diversité = pénalité si robustesse trop similaire à la moyenne de la table.
4. Sélectionne le joueur avec le meilleur score à chaque étape.

**Calcul de la robustesse Commander (après chaque round) :**
```
robustness(J) = Σ (n_joueurs + 1 - rang_adversaire)
```
Où le rang est la position dans le classement courant. Un adversaire bien classé contribue davantage.

### Détection des répétitions (Standard)

`would_have_repetitions()` simule le round suivant et calcule :
```
taux = (paires déjà rencontrées) / (total de paires) × 100
```
Si > 0%, le bouton "🔀 Round varié" apparaît dans les contrôles.

### Standings MTG officiels

Voir [section 3.7](#37-standings).

### Propagation des gagnants (Bracket)

Dans `Bracket.record_result(match_id, winner_id)` :
1. Marque le match comme terminé avec `winner_id`.
2. Lit `match.next_match_id`.
3. Dans le match suivant : si `player1_id` est `None`, y place le gagnant ; sinon dans `player2_id`.
4. Vérifie si tous les matches de la `Finale` sont terminés → `bracket.finished = True`.

---

## 9. Sérialisation JSON

### Structure de `tournaments.json`

```json
[
  {
    "id": 0,
    "name": "Tournoi Exemple",
    "format": "⚔️ Duel Commander",
    "date": "01/04/2026",
    "max_rounds": 4,
    "archived": false,
    "podiums_recorded": false,
    "pairing_system": "swiss",
    "bye_history": [2],
    "players": [
      {
        "id": 0, "name": "Alice", "score": 9, "robustness": 0,
        "reward_claimed": false, "commander": "Tymna / Thrasios",
        "buchholz": 15.0, "sos": 5.0, "had_bye": false
      }
    ],
    "rounds": [
      {
        "number": 1,
        "state": "finished",
        "tables": [
          {
            "number": 1,
            "player_ids": [0, 1],
            "finished": true,
            "results": {"0": 1, "1": 3},
            "game_scores": {"0": 2, "1": 1}
          }
        ]
      }
    ],
    "bracket": {
      "bracket_type": "demi",
      "finished": false,
      "matches": [
        {
          "match_id": 0, "round_name": "demi", "position": 0,
          "player1_id": 0, "player2_id": 2,
          "winner_id": null, "finished": false, "next_match_id": 2
        }
      ]
    }
  }
]
```

**Notes importantes :**
- Les clés de `results` et `game_scores` sont des strings en JSON (les dicts Python avec int-keys sont sérialisés en string-keys par `json.dumps`).
- `Table` sérialise uniquement `player_ids` (liste d'entiers). Les objets `Player` sont reconstruits depuis `players_by_id` lors du chargement.
- `bye_history` : sérialisé comme liste, restauré comme `set`.
- `bracket` : `null` si la phase bracket n'a pas été lancée.

### Structure de `regular_players.json`

```json
[
  {
    "id": 0,
    "pseudo": "Alice",
    "full_name": "Alice Dupont",
    "phone": "+33 6 12 34 56 78",
    "top_1": 2, "top_2": 1, "top_3": 0,
    "points": 47,
    "tournaments_played": 8
  }
]
```

### Structure de `config.json`

```json
{"theme": "dark"}
```

---

## 10. Styles QSS

Les styles sont organisés en fichiers thématiques. Chaque thème (`dark_green` / `light_green`) possède 7 fichiers :

| Fichier | Contenu |
|---|---|
| `*_main.qss` | Sidebar, fenêtre principale, nav buttons |
| `*_dashboard.qss` | Tuiles, cartes de tables, classement, boutons d'action |
| `*_tournament.qss` | Vue tournois, cartes, dialogs de création |
| `*_player.qss` | Vue joueurs, formulaires |
| `*_stats.qss` | Onglets stats, graphiques, head-to-head |
| `*_setting.qss` | Vue paramètres |
| `*_widget.qss` | Composants partagés (scroll areas, etc.) |

**ObjectNames QSS notables (dashboard) :**

| ObjectName | Composant |
|---|---|
| `PrimaryButton` | Bouton principal (vert) |
| `SecondaryButton` | Bouton secondaire (neutre) |
| `FinishButton` | "Terminer le tournoi" (doré) |
| `WarningButton` | "Round varié" (ambre) |
| `BracketButton` | "Lancer le bracket" (marron/or) |
| `ArchiveButton` | "Archiver" (bleu-gris) |
| `DangerButton` | "Réinitialiser" (rouge) |
| `BracketWinnerButton` | Boutons vainqueur dans le dialog bracket |
| `DashboardCard` | Carte principale (ranking, tables) |
| `DashboardTile` | Tuile KPI |
| `TableCard` | Carte d'une table ou d'un match bracket |
| `TableCardTitle` | Titre de la carte table |
| `TableCardWinner` | Label gagnant (vert) |
| `TableCardFinished` | Label "Terminée" |
| `TableCardRunning` | Label "En cours" |
| `RepetitionWarning` | Avertissement répétitions |
| `BO3ScoreButton` | Boutons radio BO3 dans le dialog résultats |

---

## 11. Tests

**Fichier :** `tests/test_standings.py`

Tests unitaires pour `core/standings.py` uniquement. Pas de dépendance Qt.

**Exécution :**
```bash
cd /path/to/MagicTable
PYTHONPATH=src python -m pytest tests/ -v
```

**Helpers de test :**
- `_make_tournament(players, rounds)` — crée un tournoi minimal
- `_make_finished_table(number, p1, p2, winner_id)` — table 1v1 terminée
- `_make_bye_table(number, player)` — table bye terminée
- `_find(standings, player_id)` — cherche une entrée dans les standings

**Groupes de tests :**

| Classe | Ce qui est testé |
|---|---|
| `TestBasicScoring` | W=3pts, L=0pts, accumulation multi-rounds |
| `TestMWPercent` | MW% à 100%, 0%, 50% ; 0 match = 0.0 |
| `TestOMWPercent` | Plancher 0.33, aucun adversaire, moyenne multi-adversaires |
| `TestByeHandling` | Bye = 3pts, pas d'adversaire pour OMW%, combinaison bye + match réel |
| `TestUnplayedMatch` | Tables non terminées ignorées |
| `TestSortOrder` | Tri par points, OMW% en cas d'égalité, nom alphabétique |
| `TestGWPlaceholder` | GW%/OGW% = 0.0 sans données BO3 |

---

## 12. Dépendances

**Dépendances requises :**

| Package | Version | Usage |
|---|---|---|
| `PySide6` | 6.x | Framework Qt (UI, signaux, timer, multimedia) |

**Dépendances optionnelles :**

| Package | Version | Usage |
|---|---|---|
| `fpdf2` | 2.x | Export PDF des tournois |

**Dépendances de développement :**

| Package | Usage |
|---|---|
| `pytest` | Exécution des tests unitaires |

**Modules Python standard utilisés :** `dataclasses`, `datetime`, `json`, `math`, `os`, `pathlib`, `random`, `sys`, `enum`

---

*Document généré le 31/03/2026 — MagicTable v2.0*
