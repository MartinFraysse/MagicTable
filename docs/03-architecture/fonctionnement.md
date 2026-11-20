# Fonctionnement

> La carte du code : les quatre couches, le rôle de chaque module et le chemin d'une ronde, du clic au fichier JSON.

## Les couches

```
┌──────────────────────── src/ui/ (PySide6) ────────────────────────┐
│ main_window · dashboard/ · tournaments/ · players/ · stats/ · …   │
└──────┬───────────────────────────────────────────────┬────────────┘
       │ appelle                                       │ lit, sauve
       ▼                                               ▼
┌──────── src/core/ (sans Qt) ─────────┐    ┌──── src/storage/ ────┐
│ Tournament · Round · Table · Player  │    │ un JsonStorage par   │
│ swiss_pairing · standings · bracket  │    │ fichier de data/     │
│ ranking · stats_analyzer · league    │    └──────────┬───────────┘
└──────────────────────────────────────┘               ▼
       ▲                                        src/data/*.json
       └──── src/export/ (PDF, fpdf2)
```

Règles de dépendance :

- `core/` ne connaît ni Qt, ni `ui/`, ni `storage/` : toute la logique métier se teste sans interface.
- `storage/` ne dépend que de `core/` (pour convertir les fiches de joueurs réguliers).
- `ui/` orchestre : il appelle `core/` pour calculer et `storage/` pour lire et écrire.

## Les modules du cœur

| Module | Rôle |
|---|---|
| `core/tournament.py` | L'entité centrale : joueurs, rondes, bracket, abandons, sérialisation (`to_dict` / `from_dict`). `create_round()` crée la ronde suivante. |
| `core/round.py`, `core/table.py`, `core/player.py` | Une ronde (états `preparation`, `in_progress`, `finished`), une table (joueurs, résultats, manches), un joueur du tournoi. |
| `core/swiss_pairing.py` | L'appariement Swiss des formats 1v1. |
| `core/standings.py` | Le classement MTG officiel (points, OMW%, GW%, OGW%). |
| `core/bracket.py` | La phase finale : matchs, propagation des vainqueurs, forfaits. |
| `core/ranking.py` | Le classement final d'un tournoi (bracket puis rondes) et le barème Commander. Point d'entrée unique pour le dashboard, l'historique, les stats, les ligues et le PDF. |
| `core/formats.py` | La liste des formats et `is_multiplayer_format()`. |
| `core/stats_analyzer.py` | Statistiques des joueurs (par nom et par joueur régulier) et tête-à-tête, à partir des tournois archivés. |
| `core/commander_stats.py` | Statistiques par commandant. |
| `core/league.py` | Ligues et classement cumulé. |
| `core/regular_player.py`, `core/commander.py` | Fiche d'un joueur régulier, d'un commandant. |
| `core/theme_manager.py` | Thème sombre / clair, mémorisé dans `data/config.json`. |

## L'interface

| Dossier | Rôle |
|---|---|
| `ui/main_window.py` | La fenêtre : barre de navigation à gauche, un onglet par vue. |
| `ui/dashboard/` | Le tournoi en cours : tables, classement, chrono, contrôles de ronde, bracket, projection. Plusieurs tournois peuvent tourner en parallèle (un onglet chacun). |
| `ui/tournaments/` | Création des tournois, zone de lancement (inscriptions), historique. |
| `ui/players/`, `ui/stats/`, `ui/league/`, `ui/commanders/` | Joueurs réguliers, statistiques, ligues, commandants. |
| `ui/settings_view.py` | Paramètres : chrono, données, mise à jour. |

Les vues communiquent par **signaux Qt**. Le plus important est `tournament_changed` du dashboard :
à chaque modification d'un tournoi, la vue Tournois sauvegarde l'ensemble dans `tournaments.json`.

## Une ronde, du clic au fichier

```
« Round suivante »
   │
   ▼
Tournament.create_round()
   ├─ clôture la ronde précédente (état finished)
   ├─ format 1v1 ─▶ create_round_swiss()
   │                 ├─ sync_byes()          byes depuis les tables
   │                 ├─ sync_match_points()  points 3/1/0
   │                 └─ generate_swiss_pairings()  couplage optimal
   └─ Commander ──▶ tables 3-4 par score, échanges anti-revanche
   │
   ▼
Dashboard : tables ─▶ « Lancer le round » ─▶ saisie des résultats
   │                                              │
   │      standings recalculés à chaque résultat ◀┘
   ▼
tournament_changed ─▶ TournamentStorage.save() ─▶ tournaments.json
```

Les scores ne sont jamais « additionnés » au fil de l'eau en 1v1 : ils sont **recalculés** depuis les
résultats bruts des tables. Une correction de résultat ou une annulation (Ctrl+Z) donne donc toujours
un classement juste.

## Annulation

Avant chaque modification, le dashboard prend un instantané du tournoi (`core/tournament_history.py`).
`Ctrl+Z` ou « Annuler » restaure le dernier instantané en place, sans changer d'objet.

## Persistance

Chaque ressource a sa classe de stockage dans `storage/` (`TournamentStorage`, `RegularPlayerStorage`,
`LeagueStorage`, `CommanderStorage`) qui lit et écrit un fichier JSON entier. L'emplacement du dossier
de données dépend du mode de lancement : voir la page Données du chapitre Référence.

## Voir aussi

- [Appariements et classements](appariements-et-classements.md)
- [Données](../04-reference/donnees.md)
