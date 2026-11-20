# Présentation

> MagicTable en une page : ce que c'est, pour qui, et par où commencer dans cette documentation.

## Le projet

MagicTable est une application de bureau pour **organiser des tournois de jeux de cartes** :
Magic: The Gathering (Commander, Duel Commander, Draft, Avant-Première), Pokémon, Rise.

L'organisateur y inscrit les joueurs, lance les rondes, saisit les résultats et suit le classement en direct.
L'application calcule les appariements, les départages officiels et la phase finale, puis garde l'historique
pour les statistiques et les ligues.

```
 Inscriptions ─▶ Rondes ─────────▶ Phase finale ─▶ Archive
      │          Swiss / tables     Top 2 / 4 / 8      │
      │          résultats, chrono                     ▼
      └─────── joueurs réguliers ◀──────── statistiques, ligues
```

## Ce qu'elle fait

| Domaine | En bref |
|---|---|
| Tournois | 6 formats, Swiss pour le 1v1, tables de 3-4 joueurs pour le Commander multi |
| Rondes | chrono, saisie des résultats (BO3), abandons, annulation (Ctrl+Z), fenêtre de projection |
| Classement | standings MTG officiels : points, OMW%, GW%, OGW% |
| Phase finale | Top 2, Top 4 ou Top 8 avec petite finale |
| Après le tournoi | historique, export PDF, statistiques des joueurs et des commandants, ligues |

L'application est **100&nbsp;% locale** : les données sont des fichiers JSON sur l'ordinateur, sans serveur ni compte.
Elle tourne sous Linux et Windows (exécutable `.exe` qui se met à jour seul).

## À qui s'adresse cette documentation

- **L'organisateur de tournois**, qui veut installer et utiliser l'application.
- **Le développeur**, qui veut comprendre le code, le modifier ou publier une version.

## Par où commencer

| Je veux… | Chapitre |
|---|---|
| comprendre un terme (Swiss, bye, OMW%…) | Présentation, page Glossaire |
| installer et lancer l'application | Guides, page Installation |
| organiser mon premier tournoi | Guides, page Organiser un tournoi |
| suivre mes joueurs, mes stats, une ligue | Guides, page Joueurs et statistiques |
| comprendre comment le code est construit | Architecture |
| connaître un barème, un format de fichier, une commande | Référence |
| publier une version, résoudre un problème | Exploitation |

| Page | Pour |
|---|---|
| [Glossaire](glossaire.md) | les termes du tournoi et de l'application |
