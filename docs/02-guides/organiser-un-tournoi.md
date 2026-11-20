# Organiser un tournoi

> De la création du tournoi à son archivage : inscriptions, rondes, résultats, abandons, phase finale.

## En bref

```
🏆 Tournois
  ➕ Nouveau tournoi ─▶ carte « À venir »
        │ glisser
        ▼
  zone « Lancer un tournoi » : inscriptions ─▶ 🚀 Lancer le tournoi
                                                     │
📊 Dashboard                                         ▼
  ▶ Lancer le round ─▶ résultats ─▶ ⏭ Round suivante   (× N rondes)
        │
        ├─ 1v1 : 🏆 Lancer le bracket ─▶ ⏭ Phase suivante
        ▼
  🏁 Terminer ─▶ CLASSEMENT FINAL ─▶ Fermer = archive
```

## 1. Créer le tournoi

Onglet **🏆 Tournois** → « ➕ Nouveau tournoi ».

| Champ | Détail |
|---|---|
| Nom du tournoi | obligatoire |
| Format | Commander, Duel Commander, Draft, AP, Pokemon, Rise |
| Date | `JJ/MM/AAAA`, obligatoire |
| Nombre de rounds | de 1 à 10 (3 par défaut) |
| Ligue | « Aucune ligue » ou une ligue existante |

Le tournoi apparaît dans « ⏳ Tournois à venir ». Clic droit sur sa carte : « ✏️ Modifier le tournoi »,
« 🚀 Envoyer vers Launch », « 🗑️ Supprimer le tournoi ».

Le système d'appariement découle du format : Swiss pour tous les formats 1v1, tables de 3-4 pour le Commander.

## 2. Inscrire les joueurs

Glisser la carte dans la zone **« 🎮 Lancer un tournoi »** (ou « 🚀 Envoyer vers Launch »).

- **Saisie** : taper un nom puis « ➕ Ajouter ». L'autocomplétion propose les joueurs réguliers :
  `Tab` ouvre la liste et passe d'une suggestion à l'autre, `Entrée` ajoute le joueur.
- **Liste des joueurs réguliers** : le bouton « 👥 » ouvre « Joueurs permanents ». Un clic inscrit le joueur ;
  un clic sur un joueur déjà inscrit (✔) le désinscrit.
- **Clic droit sur un inscrit** : « 🛡️ Ajouter un commandant » (Commander et Duel Commander),
  « ➕ Ajouter aux joueurs permanents », « ✏️ Modifier », « 🗑️ Supprimer ». Le double-clic ouvre le choix du commandant.

Inscrire les joueurs depuis la liste des joueurs réguliers relie le tournoi à leur fiche : leurs statistiques
seront comptées sans ambiguïté.

### Conditions pour lancer

| Format | Condition |
|---|---|
| Commander | au moins 6 joueurs ; commandant facultatif (⚠️ devant le nom s'il manque) |
| Duel Commander | au moins 4 joueurs, **tous avec un commandant** |
| Autres formats | au moins 4 joueurs |

La zone affiche le nombre de tables et le nombre de rondes recommandé. Si le nombre de rondes du tournoi
s'en écarte, une confirmation est demandée au lancement.

Cliquer sur **« 🚀 Lancer le tournoi »** : l'application ouvre le Dashboard sur la ronde 1.

## 3. Jouer une ronde

Le Dashboard affiche les tuiles du tournoi (joueurs, tables, ronde, chrono), les tables et l'aperçu du classement.

1. **« ▶ Lancer le round »** démarre le chrono. C'est obligatoire avant de saisir un résultat.
2. **Saisir les résultats** : double-clic sur une table (ou clic droit → « ✏️ Définir les résultats »).

| Format | Saisie |
|---|---|
| 1v1 | manches gagnées par chaque joueur : 2-0, 2-1, 1-1, 1-2, 0-2, ou 1-0 / 0-1 |
| Commander | « Vainqueur » puis « Second » ; les autres sont 3<sup>e</sup>-4<sup>e</sup> |

3. Le classement se met à jour à chaque résultat. Une table **BYE** affiche « ⚖️ Victoire automatique ».
4. Quand toutes les tables sont terminées : **« ⏭ Round suivante »**. Au dernier round, le bouton devient « 🏁 Terminer le tournoi ».

À la fin du chrono, un son retentit ; la ronde ne passe pas seule à la suivante.

### Avant les résultats de la ronde 1

**« ✏️ Modifier les pairings »** permet d'échanger deux joueurs de tables différentes (ou le joueur au bye),
puis « Confirmer les pairings ». Le bouton disparaît dès qu'un résultat est saisi.

### Commander : trop de revanches

Si la ronde suivante ferait rejouer beaucoup d'adversaires, le message « ⚠️ X% de répétitions » apparaît avec
**« 🔀 Round varié »**, qui compose une ronde plus mélangée.

## 4. Abandons et corrections

| Action | Comment | Effet |
|---|---|---|
| Abandon d'un joueur | clic droit dans le classement → « 🚪 Retirer du tournoi » | il garde ses résultats et n'est plus apparié ; son match en cours est perdu 0-2 (1v1) ou il prend la dernière place de sa table (Commander) |
| Corriger un résultat | double-cliquer à nouveau sur la table | classement recalculé |
| Annuler | « ↩ Annuler » ou `Ctrl+Z` | jusqu'à 20 actions en arrière |
| Tout recommencer | « 🔄 Réinitialiser le tournoi » | supprime rondes et résultats, recrée la ronde 1 |
| Mettre de côté | « 🚪 Quitter le tournoi » | ferme l'onglet ; le tournoi est conservé et peut être relancé |

Clic droit sur un joueur du classement : « 📋 Résumé des rounds » montre son parcours.

## 5. Phase finale (formats 1v1)

Après la dernière ronde, avec au moins 4 joueurs actifs, **« 🏆 Lancer le bracket »** apparaît.

| Choix | Disponible à partir de | Matchs |
|---|---|---|
| Top 2 | 2 joueurs | finale (+ petite finale dès 4 joueurs) |
| Top 4 | 4 joueurs | demi-finales, finale, petite finale |
| Top 8 | 8 joueurs | quarts, demi-finales, finale, petite finale |

Pour chaque phase : « ▶ Lancer le round », puis clic droit sur un match → « ✏️ Définir le vainqueur »,
puis **« ⏭ Phase suivante »**. Les seeds suivent le classement des rondes ; un joueur sans adversaire passe
directement au tour suivant.

Attention : cliquer sur « 🏁 Terminer le tournoi » au lieu de « 🏆 Lancer le bracket » termine le tournoi sans phase finale.

## 6. Terminer et archiver

À la fin, l'écran **« CLASSEMENT FINAL »** s'affiche (bracket en tête, puis classement des rondes).
Le bouton **« Fermer » archive le tournoi** et ferme son onglet.

Le tournoi rejoint **« 📜 Historique des tournois »** (onglet Tournois). Clic droit sur une carte :

| Entrée | Effet |
|---|---|
| 📋 Détails | classement final ; « 📋 Voir le parcours » d'un joueur |
| 🎁 Récompenses | cocher les joueurs qui ont récupéré leur lot |
| 📄 Exporter PDF | podium, classement et détail des rondes |
| 🗑️ Supprimer définitivement | retire le tournoi de l'historique et des statistiques |

## Plusieurs tournois en même temps

Chaque tournoi lancé a son **onglet** dans le Dashboard (⚔️ pour le 1v1, 👑 pour le Commander).
Le « × » d'un onglet équivaut à « Quitter le tournoi ».

## Projection pour les joueurs

**« 📺 Afficher la projection »** ouvre une fenêtre à placer sur un second écran : numéro de ronde, chrono
(vert, jaune sous 10 min, rouge sous 5 min) et tables. `F11` ou `F` passe en plein écran, `Échap` en sort.
