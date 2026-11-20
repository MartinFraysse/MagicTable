# Données

> Où MagicTable range ses données et ce que contient chaque fichier JSON.

## Emplacement

| Mode de lancement | Dossier des données |
|---|---|
| Depuis les sources (`python src/app.py`) | `src/data/` |
| Exécutable Windows (`MagicTable.exe`) | `%APPDATA%\MagicTable\data` |
| Exécutable Linux | dossier `data/` à côté du binaire |

Le dossier est créé au premier lancement. Pour sauvegarder ou changer d'ordinateur, il suffit de copier ce dossier.

## Les fichiers

| Fichier | Contenu | Classe de stockage |
|---|---|---|
| `tournaments.json` | tous les tournois, à venir, en cours et archivés | `TournamentStorage` |
| `regular_players.json` | les fiches des joueurs réguliers (données personnelles : non suivi par git) | `RegularPlayerStorage` |
| `leagues.json` | les ligues | `LeagueStorage` |
| `commanders.json` | les commandants | `CommanderStorage` |
| `commander_images/` | les images des commandants (nom aléatoire `.jpg`) | — |
| `config.json` | les préférences (thème) | `ThemeManager` |

Chaque fichier est une **liste JSON**, réécrite en entier à chaque sauvegarde, en UTF-8.
Un fichier absent ou vide est lu comme une liste vide.

## `tournaments.json`

```json
{
  "id": 2,
  "name": "Avant Première Strixhaven",
  "format": "🏆 AP",
  "date": "15/04/2026",
  "max_rounds": 3,
  "archived": true,
  "pairing_system": "swiss",
  "bye_history": [5],
  "players": [
    {
      "id": 0, "name": "Alice", "score": 9, "robustness": 0,
      "reward_claimed": false, "commander": "",
      "had_bye": false, "dropped": false, "regular_player_id": 1
    }
  ],
  "rounds": [
    {
      "number": 1,
      "state": "finished",
      "tables": [
        {
          "number": 1, "player_ids": [0, 3], "finished": true,
          "results": {"0": 1, "3": 2},
          "game_scores": {"0": 2, "3": 1}
        }
      ]
    }
  ],
  "bracket": null
}
```

| Champ | Sens |
|---|---|
| `date` | format `JJ/MM/AAAA` |
| `pairing_system` | `swiss` (formats 1v1) ou `standard` (Commander) ; recalculé depuis le format à l'enregistrement |
| `bye_history`, `had_bye` | joueurs ayant reçu un bye ; recalculés depuis les tables d'un seul joueur |
| `players[].score` | points de match (1v1) ou points Commander |
| `players[].regular_player_id` | lien vers une fiche de `regular_players.json`, ou `null` |
| `rounds[].state` | `preparation`, `in_progress` ou `finished` |
| `tables[].results` | identifiant du joueur → place (1 = vainqueur ; même place des deux côtés = nul) |
| `tables[].game_scores` | identifiant du joueur → manches gagnées (BO3) |
| `bracket` | phase finale : `bracket_type` (`final`, `demi`, `quart`), `matches` (joueurs, vainqueur, match suivant), `finished` |

Les clés des dictionnaires `results` et `game_scores` sont des chaînes en JSON et des entiers une fois chargées.

## `regular_players.json`

```json
{
  "id": 1,
  "pseudo": "Alice",
  "full_name": "Alice Martin",
  "phone": "06 12 34 56 78"
}
```

Aucune statistique n'est stockée : elles sont recalculées depuis les tournois archivés.
Les anciens champs (`top_1`, `points`, `discord_id`…) sont ignorés et disparaissent à la sauvegarde suivante.

## `leagues.json`

```json
{
  "id": 0,
  "name": "Ligue Commander",
  "format": "👑 Commander",
  "season": "2026",
  "tournament_ids": [3, 5],
  "scoring": {"1": 12, "2": 9, "3": 7, "4": 5,
              "5": 3, "6": 3, "7": 2, "8": 2},
  "participation_pts": 1
}
```

## `commanders.json`

```json
{
  "id": 3,
  "name": "Lightning, Army of One",
  "colors": ["W", "R"],
  "image_path": "commander_images/cf4cd2fc6f14.jpg",
  "duel": true
}
```

`colors` : lettres WUBRG (blanc, bleu, noir, rouge, vert). `image_path` : relatif au dossier des données.

## Voir aussi

- [Fonctionnement](../03-architecture/fonctionnement.md)
