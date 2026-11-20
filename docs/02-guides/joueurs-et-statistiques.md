# Joueurs et statistiques

> Gérer les joueurs réguliers et les commandants, consulter les statistiques, animer une ligue, régler l'application.

## Joueurs réguliers

Onglet **👥 Joueurs**. Un joueur régulier est une fiche réutilisée de tournoi en tournoi.

- « ➕ Ajouter un joueur » : « Pseudo » (obligatoire, unique), « Nom complet », « Téléphone » (10 chiffres).
- « 🔍 Rechercher un joueur… » filtre sur le pseudo et le nom.
- Double-clic : modifier. `Suppr` : supprimer (avec confirmation).
- Clic droit → « 📊 Statistiques » : podiums, tournois joués, points.

Le tableau (points, 🥇 🥈 🥉, podiums) est **calculé à partir des tournois archivés**. Un joueur de tournoi compte
pour une fiche s'il a été inscrit depuis la liste des joueurs réguliers, ou s'il porte exactement le même pseudo.

Un joueur inscrit à la main peut devenir régulier : clic droit → « ➕ Ajouter aux joueurs permanents »
(zone de lancement ou classement du Dashboard) ; il est alors relié à sa nouvelle fiche.

## Commandants

Onglet **👑 Commandants**. « 🔍 Rechercher un commandant… », filtre « ⚔️ Duel ».

« ➕ Ajouter un commandant » :

| Champ | Détail |
|---|---|
| Nom | obligatoire ; propositions de la base Scryfall dès 2 caractères, filtrées par les couleurs cochées |
| Couleurs | W, U, B, R, G (aucune = incolore) |
| ⚔️ Duel Commander | à cocher s'il est joué en Duel |
| Image de fond | « 📁 Choisir… » un fichier, ou « 🔍 Scryfall » pour télécharger l'illustration |

Double-clic sur un commandant : ses statistiques, en onglets « ⚔️ Duel » et « 👑 Multi » (palmarès, victoires,
défaites, nuls, joueurs qui l'ont joué). En Duel, « ⚔️ Voir les Matchups » donne son bilan contre chaque adversaire.

Le commandant d'un joueur se choisit dans la zone de lancement (double-clic sur l'inscrit). La boîte
« 🛡️ Choisir un commandant » permet aussi d'en créer un (« ➕ Nouveau »).

## Statistiques

Onglet **📈 Stats**, calculé sur les **tournois archivés** uniquement.

| Sous-onglet | Contenu |
|---|---|
| Stats Globales | tournois joués, joueurs uniques, tables jouées ; répartition des formats ; commandants les plus victorieux et les plus joués |
| Classement | les joueurs réguliers : points, tournois, podiums, top 1 / 2 / 3 |
| Head-to-Head | choisir un joueur : son bilan contre chaque adversaire (matchs, victoires, défaites, winrate) ; double-clic pour l'historique des rencontres |

## Ligues

Onglet **🏅 Ligue**. Une ligue cumule les résultats de plusieurs tournois archivés d'un même format.

1. « + Nouvelle ligue » : nom, saison, format, barème de points par place (par défaut 12, 9, 7, 5, 3, 3, 2, 2,
   puis 1 point de participation).
2. « + Ajouter un tournoi » : seuls les tournois archivés du même format sont proposés. Un tournoi peut aussi
   être rattaché à une ligue dès sa création.
3. Le **classement** (points, tournois, meilleure place) se met à jour seul ; un clic sur un joueur montre son
   parcours dans la ligue.

« ✕ » retire un tournoi de la ligue, sans confirmation. Supprimer une ligue ne supprime pas ses tournois.

## Paramètres

Onglet **⚙️ Paramètres**.

| Section | Contenu |
|---|---|
| Durée des rounds | durée du chrono pour les tournois ouverts ensuite, de 1 à 120 min (50 par défaut). Non mémorisée : revient à 50 min au redémarrage |
| Systèmes de notation par format | rappel des barèmes (texte informatif) |
| Gestion des données | compteurs et suppressions en masse : tournois archivés, tous les tournois, joueurs, commandants (et leurs images), ligues. **Irréversible** : copier d'abord le dossier des données |
| Mise à jour | « 🔍 Vérifier les mises à jour », puis « ⬇ Télécharger et installer » et « 🔄 Redémarrer et installer » (exécutable uniquement) |
| À propos | version de l'application |

