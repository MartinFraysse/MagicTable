# Formats et barème

> Les formats de tournoi, leurs effectifs minimum, leurs points et leurs départages, et le barème par défaut des ligues.

## Formats

| Format (tel qu'affiché) | Joueurs par table | Minimum pour lancer | Appariement | Phase finale |
|---|---|---|---|---|
| 👑 Commander | 3 ou 4 | 6 | tables 3-4 par score + robustesse | non |
| ⚔️ Duel Commander | 2 | 4 | Swiss | Top 2 / 4 / 8 |
| 🃏 Draft | 2 | 4 | Swiss | Top 2 / 4 / 8 |
| 🏆 AP | 2 | 4 | Swiss | Top 2 / 4 / 8 |
| ⚡ Pokemon | 2 | 4 | Swiss | Top 2 / 4 / 8 |
| 🔥 Rise | 2 | 4 | Swiss | Top 2 / 4 / 8 |

- **Duel Commander** : chaque joueur actif doit avoir un commandant pour pouvoir lancer le tournoi.
- Le libellé exact (emoji compris) est enregistré dans les tournois et les ligues : `core/formats.py`.
- Nombre de rondes Swiss recommandé : `⌈log₂(joueurs)⌉` (4-8 joueurs → 3, 9-16 → 4, 17-32 → 5).

## Points

### Formats 1v1

| Résultat | Points de match |
|---|---|
| Victoire (2-0, 2-1, 1-0) | 3 |
| Nul (1-1) | 1 |
| Défaite | 0 |
| Bye | 3 (victoire 2-0) |
| Victoire par forfait (abandon de l'adversaire) | 3 (2-0) |

### Commander multi

| Place à la table | Points |
|---|---|
| 1<sup>re</sup> | 3 |
| 2<sup>e</sup> | 2 |
| 3<sup>e</sup> et 4<sup>e</sup> | 1 |
| Abandon en cours de ronde | dernière place de sa table |

## Départages

| Format | Ordre de classement |
|---|---|
| 1v1 | points de match → OMW% → GW% → OGW% → nom |
| Commander multi | score → robustesse → nom |
| Avec phase finale | résultat du bracket, puis l'ordre ci-dessus à stade égal |

Planchers : chaque adversaire compte au minimum **33 %** dans l'OMW% et l'OGW%.

## Ligues : barème par défaut

Chaque tournoi archivé d'une ligue rapporte des points selon la place finale. Le barème se modifie à la création de la ligue.

| Place | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | au-delà |
|---|---|---|---|---|---|---|---|---|---|
| Points | 12 | 9 | 7 | 5 | 3 | 3 | 2 | 2 | 1 (participation) |

Classement de ligue : total de points → meilleure place obtenue → nom.

## Voir aussi

- [Appariements et classements](../03-architecture/appariements-et-classements.md)
