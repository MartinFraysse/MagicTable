# 0003 — Statistiques calculées depuis les archives

> Pourquoi les points et podiums des joueurs réguliers ne sont plus stockés.

- **Date :** 2026-11-20
- **Statut :** acceptée

## Contexte

Les statistiques des joueurs réguliers avaient deux sources : des compteurs enregistrés dans la fiche à la fin
de chaque tournoi (points, podiums, tournois joués) et un recalcul depuis les tournois archivés.
Les écrans n'utilisaient pas la même source et pouvaient afficher des chiffres différents.

## Décision

Une seule source : les **tournois archivés**. `StatsAnalyzer` recalcule tout à l'ouverture des vues.
Un joueur de tournoi est rattaché à une fiche par son lien explicite (`regular_player_id`), sinon par pseudo
identique (insensible à la casse), pour les tournois archivés avant l'existence du lien.

## Conséquences

- La vue Joueurs, la fiche Statistiques et l'onglet Stats affichent toujours les mêmes chiffres.
- Corriger ou supprimer un tournoi archivé corrige les statistiques.
- Les anciens compteurs de `regular_players.json` sont ignorés et disparaissent à la prochaine sauvegarde.
- Un joueur inscrit sous un autre pseudo et sans lien n'est pas compté pour sa fiche.
