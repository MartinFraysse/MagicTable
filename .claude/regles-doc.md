# Règles de la documentation (notes `docs/.claude_doc.md` et pages `docs/`)

## Les trois étapes

```
travail ──▶ docs/.claude_doc.md ──« rédige la doc »──▶ docs/NN-chapitre/*.md ──genpdf──▶ docs/pdf/<projet>.pdf
            (notes, sans demander)                     (pages, sur demande)              (export)
```

- **Les notes** (`docs/.claude_doc.md`) : Claude y range seul, au fil du travail, ce que la doc devra dire.
  Commitées, mais exclues du PDF (fichier caché).
- **Les pages** (`docs/NN-chapitre/*.md`) : écrites **seulement sur demande**, à partir des notes.
- **Le PDF** : généré par `genpdf` à partir des pages ; jamais modifié à la main.

Ce n'est ni le site de suivi (propositions et réalisations, voir `regles-site.md`), ni le journal (l'historique).
Les conventions des pages (format, liens, images, ADR) sont dans `docs/README.md`.

## Le plan : propre à chaque projet

Les chapitres et les pages **ne sont pas fixés par le modèle** : ils dépendent du projet
(une appli n'a pas la même doc qu'une bibliothèque, un script ou un site).

- Le plan est un **choix** : Claude le propose sur le site de suivi (sujet « Plan de la documentation »),
  au plus tard à la première demande « rédige la doc », ou plus tôt si les notes deviennent nombreuses.
  Il part des besoins du lecteur (découvrir, installer, utiliser, comprendre, chercher, exploiter),
  en s'aidant de la palette de chapitres de `docs/README.md`, et ne garde que ce qui a du contenu.
- Une fois validé, il est recopié dans la section « Plan » des notes : c'est la référence.
- Le changer (ajouter, fusionner, renommer un chapitre ou une page) est aussi un choix : le proposer d'abord.
  On ne renumérote pas un chapitre existant ; un nouveau prend le numéro suivant.

## Les notes (`docs/.claude_doc.md`)

### Quand écrire (sans demander)

- on comprend comment une partie fonctionne (composant, flux, script, config) ;
- une commande, une variable, un paramètre ou une étape d'installation utile apparaît ;
- un problème est résolu (symptôme → cause → solution) ;
- un sujet du site passe à `fait` et change ce que la doc devra dire ;
- quelque chose noté ici, ou écrit dans une page de `docs/`, devient faux.

### Comment écrire

- Une sous-section **par page visée**, avec le fichier cible dans le titre :
  `### Installation — 02-guides/installation.md`. Tant que le plan n'existe pas, ou si aucune page ne convient :
  `### Sauvegardes — (à placer)`. Ne créer une sous-section que lorsqu'il y a quelque chose à y mettre.
- Une note qui **corrige une page déjà écrite** le dit : `Corrige : 02-guides/installation.md, étape 3`.
- Le **présent** seulement : corriger ou remplacer une information périmée, ne pas empiler (l'historique va dans le journal).
- Les **décisions** ne sont pas recopiées : un lien vers la page sujet du site suffit.
- Factuel et court, pas de secret. Mettre à jour la date « Dernière mise à jour ».

Dans le terminal, à chaque mise à jour, **une ligne** :

```
📝 doc : <ce qui a été ajouté ou corrigé> → docs/.claude_doc.md
```

## « Rédige la doc » : la procédure

1. **Plan.** Pas de plan validé, ou des notes « (à placer) » qui n'entrent dans aucune page :
   proposer le plan (ou son changement) sur le site, et **attendre la décision**.
2. **Pages.** Pour chaque note : créer ou mettre à jour la page visée, selon les modèles de `docs/README.md`
   (une page d'installation commence par la liste simple « À installer » : un élément par ligne, le nom seul).
   Réécrire proprement, pour un lecteur qui ne connaît pas l'historique : pas de « on a changé », pas de journal.
3. **Ouvertures de chapitre.** Mettre à jour l'`index.md` de chaque chapitre touché (voir ci-dessous) :
   chaque page du chapitre y est liée, **dans l'ordre de lecture voulu**.
4. **Ouverture du document.** Le premier chapitre ouvre le document : son `index.md` dit en quelques lignes
   ce qu'est le projet, à qui s'adresse la doc, et par où commencer selon le besoin (tableau besoin → chapitre).
5. **Vérifier.** Lancer `genpdf`, puis regarder les pages du PDF en image
   (`pdftoppm -r 60 -png docs/pdf/<projet>.pdf /tmp/…/p`, puis les lire) : sommaire, ouvertures de chapitre,
   tableaux, code. Corriger le `.md` et régénérer jusqu'à ce que ce soit propre.
6. **Nettoyer.** Retirer des notes ce qui a été repris ; garder ce qui ne l'a pas été.
7. **Dire** ce qui a été écrit (pages créées ou modifiées) et ce qui a été vérifié dans le PDF.

## Ce que le PDF attend des pages

`genpdf` construit le PDF à partir de la structure ; la respecter, c'est garantir un PDF propre.

| Élément | Règle | Dans le PDF |
|---|---|---|
| Chapitre | un dossier `docs/NN-nom/` (deux chiffres, tirets, sans accents) | bandeau « CHAPITRE NN », dans l'ordre des numéros |
| `index.md` | `# Titre du chapitre`, `> résumé`, quelques lignes d'introduction, puis un tableau des pages avec un lien vers chacune | ouverture du chapitre ; **l'ordre des liens fixe l'ordre des pages** |
| Page | un `.md` = un seul `#` (son titre), puis `##`, `###` | une nouvelle page, titre dans le sommaire |
| Résumé | une ligne `>` juste sous le titre de chaque page | encadré coloré |
| Liens vers une autre page | relatifs (`../04-reference/commandes.md`) | texte simple (pas cliquable) : le texte du lien doit se suffire |
| Images | `docs/assets/<chapitre>/`, chemin relatif, texte alternatif | intégrées ; une image manquante fait échouer le PDF |
| Schémas | ASCII ou image ; pas de Mermaid | — |

- L'`index.md` est une **ouverture**, pas une page de contenu : le contenu va dans les pages du chapitre.
  Un chapitre sans `index.md` prend son titre dans le nom du dossier, sur une page vide : à éviter.
- Pas de page de quelques lignes : la fusionner avec une voisine (chaque page commence une nouvelle feuille).
- « Voir aussi » seulement si les renvois aident vraiment.
