# 0002 — Swiss par couplage optimal

> Pourquoi l'appariement Swiss s'appuie sur un couplage de poids minimal (networkx).

- **Date :** 2026-11-20
- **Statut :** acceptée

## Contexte

L'ancien appariement Swiss explorait les combinaisons par retour arrière, borné à 300 000 essais.
Une simulation de plusieurs centaines de tournois a montré :

- une ronde 1 toujours appariée par ordre alphabétique (les égalités étaient départagées par le nom) ;
- des écarts de points inutiles en fin de tournoi (un 9 points contre un 0 point) dans environ 6 % des rondes ;
- 1 à 4,5 secondes de calcul au-delà de 25 joueurs, interface figée.

## Décision

Formuler chaque ronde comme un **couplage parfait de poids minimal** sur le graphe des joueurs actifs
(plus un nœud « bye » en effectif impair), avec des coûts lexicographiques :
second bye, puis revanche, puis points du joueur au bye, puis écart de points au carré, puis un aléa.
Le calcul utilise `networkx.max_weight_matching` (algorithme de blossom).

Le Swiss est appliqué à **tous les formats 1v1** ; l'ancien mode « standard » en 1v1 disparaît.

## Conséquences

- Appariement exact et reproductible dans ses règles, en quelques millisecondes à 40 joueurs.
- Ronde 1 et égalités tirées au sort, comme le prévoient les règles de tournoi MTG.
- Nouvelle dépendance `networkx` (pure Python) : `requirements.txt` et `MagicTable.spec`.
- Les règles sont vérifiées par `tests/test_swiss.py`, dont un test de qualité sur des tournois simulés.
