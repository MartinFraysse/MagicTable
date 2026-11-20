# Appariements et classements

> Les règles de calcul de MagicTable : comment les tables sont composées, comment les joueurs sont classés, comment se déroule la phase finale.

## Swiss (formats 1v1)

Fichier : `core/swiss_pairing.py`. Utilisé pour tous les formats sauf le Commander multi.

### Les priorités

Chaque ronde est **le meilleur appariement possible** selon ces règles, de la plus forte à la plus faible :

| Priorité | Règle |
|---|---|
| 1 | Pas de second bye tant qu'un autre joueur peut le recevoir. |
| 2 | Pas de revanche si une autre combinaison existe (sinon, le minimum de revanches). |
| 3 | Le bye va au joueur qui a le moins de points. |
| 4 | Les adversaires sont les plus proches possible en points. |
| 5 | Entre appariements équivalents, le hasard décide : la ronde 1 est entièrement aléatoire. |

Les joueurs ayant abandonné ne sont jamais appariés.

### Le calcul

Le problème est résolu exactement par un **couplage parfait de poids minimal** (algorithme de blossom,
`networkx.max_weight_matching`) :

```
joueurs actifs ─▶ graphe complet : une arête par paire possible
                  + un nœud BYE relié à chaque joueur (effectif impair)
                        │
                        ▼
       coût de chaque arête (chaque niveau domine les suivants)
                        │
                        ▼
       couplage parfait de coût minimal ─▶ tables + bye
```

| Arête | Coût |
|---|---|
| joueur → BYE, joueur ayant déjà eu un bye | 10²¹ |
| paire déjà jouée (revanche) | 10¹⁷ |
| joueur → BYE | 10¹³ × points du joueur |
| paire de joueurs | 10⁶ × (écart de points)² |
| toute arête | petit aléa (< 1 000) |

L'écart est compté **au carré** : deux petits décalages (9 contre 6, puis 6 contre 3) coûtent moins qu'un
gros (9 contre 0). Le résultat est exact, sans limite d'itérations, en quelques millisecondes pour 40 joueurs.

Les tables sont ensuite numérotées du haut vers le bas du classement, le mieux classé en premier.
Le bye est une table d'un seul joueur, terminée d'office, comptée comme une victoire 2-0.

## Tables Commander (multi)

Fichier : `core/tournament.py`.

### Taille des tables

À partir de 6 joueurs actifs : uniquement des tables de 3 si l'effectif est divisible par 3,
sinon le plus possible de tables de 4 complétées par des tables de 3.

| Joueurs | Tables |
|---|---|
| 6 | 3 + 3 |
| 7 | 4 + 3 |
| 8 | 4 + 4 |
| 10 | 4 + 3 + 3 |
| 11 | 4 + 4 + 3 |

### Composition

1. **Ronde 1** : ordre aléatoire.
2. **Rondes suivantes** : joueurs triés par score puis robustesse ; les tables sont remplies dans cet ordre
   (les meilleurs ensemble).
3. Des échanges entre tables voisines (jusqu'à 2 tables d'écart) réduisent les revanches,
   jusqu'à ce qu'aucun échange n'améliore plus (30 passes au plus).

Si plus de la moitié des paires de la ronde proposée se sont déjà rencontrées, le dashboard le signale et
propose **Round varié** : une composition aléatoire qui minimise les revanches, quitte à mélanger les niveaux.

### Points et robustesse

| Place à la table | Points |
|---|---|
| 1<sup>re</sup> | 3 |
| 2<sup>e</sup> | 2 |
| 3<sup>e</sup> et 4<sup>e</sup> | 1 |

La **robustesse** départage les égalités : après chaque ronde, chaque joueur reçoit, pour chaque adversaire
rencontré, `N − rang de l'adversaire` (N = nombre de joueurs, rang selon le score). Avoir affronté des joueurs
bien classés rapporte plus.

Classement Commander : score, puis robustesse, puis nom.

## Standings MTG (formats 1v1)

Fichier : `core/standings.py`. Recalculés entièrement depuis les résultats bruts à chaque changement.

| Étape | Calcul |
|---|---|
| Points de match | victoire 3, nul 1, défaite 0 ; un bye compte comme une victoire |
| MW% | points de match / (3 × matchs joués) |
| OMW% | moyenne des MW% des adversaires, chacun au minimum à 0,33 ; le bye n'est pas un adversaire |
| GW% | manches gagnées / manches jouées ; un bye compte comme 2 manches gagnées sur 2 |
| OGW% | moyenne des GW% des adversaires ayant des manches saisies, plancher 0,33 |

Ordre : **points → OMW% → GW% → OGW% → nom**.

Un match est un **nul** quand les deux joueurs ont la même place (score 1-1).
Une table sans résultat complet n'est pas comptée.

## Phase finale (bracket)

Fichier : `core/bracket.py`. Proposée après la dernière ronde des formats 1v1, à partir de 4 joueurs actifs.

| Format | Matchs |
|---|---|
| Top 2 | finale 1 contre 2 ; petite finale 3 contre 4 s'il y a au moins 4 joueurs |
| Top 4 | demi-finales 1-4 et 2-3, puis finale et petite finale |
| Top 8 | quarts 1-8, 4-5, 2-7, 3-6, puis demi-finales, finale et petite finale |

- Les seeds viennent du classement des rondes ; les joueurs ayant abandonné sont exclus et remplacés par les suivants.
- Le vainqueur d'un match passe au match suivant ; en demi-finale, le perdant va en petite finale.
- **Forfaits automatiques** : un joueur face à un abandon, ou face à une place qui ne sera jamais remplie
  (effectif réduit), gagne d'office. Une place encore **en attente** d'un match précédent n'est jamais un forfait.
- Corriger un résultat annule en cascade les matchs qui en dépendaient.

## Classement final

Fichier : `core/ranking.py`, fonction `final_ranking()`. Utilisé partout : fin de tournoi, historique,
statistiques, ligues, export PDF.

```
bracket (même partiel)          classement des rondes
  1.   vainqueur de la finale     standings MTG (1v1)
  2.   finaliste                  score + robustesse (Commander)
  3-4. petite finale                        │
  5-8. perdants des quarts ◀── départage ───┘
                                à stade égal
puis : joueurs hors bracket, dans l'ordre des rondes
```

## Voir aussi

- [Formats et barème](../04-reference/formats-et-bareme.md)
- [0002 — Swiss par couplage optimal](decisions/0002-swiss-couplage-optimal.md)
