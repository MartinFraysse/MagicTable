# Documentation — MagicTable

Ce dossier contient toute la documentation du projet, et ce fichier explique comment elle est organisée.

## Principe

Une seule source, un format d'export.

```
docs/NN-chapitre/*.md  (source, versionnée)
   │
   └──▶ PDF général (genpdf) : page de garde, sommaire, puis les chapitres ; généré, jamais édité à la main
```

- **Le Markdown est la source de vérité.** On écrit et on corrige uniquement les fichiers `.md`.
- **Le PDF est un export** construit à partir de la structure des dossiers (voir « Le PDF général »).
- **Les fichiers cachés sont exclus du PDF**, comme `README.md` et tout ce qui n'est pas dans un dossier `NN-…`.

### Ce que Claude tient à côté de la doc

- `.claude_doc.md` : le **plan** de la doc de ce projet et la **matière première** des pages, tenue par Claude au fil du travail
  (règles et procédure « rédige la doc » : `.claude/regles-doc.md`). Exclu du PDF.
- `site/` : le **site de suivi**, où Claude montre ce qu'il propose et ce qu'il a fait (règles : `.claude/regles-site.md`).
  Ce n'est pas la doc : il est hors PDF.

## Les chapitres : un plan par projet

Les chapitres et les pages **dépendent du projet** : le plan est choisi pour lui (proposé par Claude, validé par l'utilisateur)
et noté dans `.claude_doc.md`. Chaque page répond à **un seul** besoin du lecteur, dans l'esprit de [Diátaxis](https://diataxis.fr/)
(apprendre, faire, chercher une information, comprendre).

La structure, elle, est toujours la même :

```
docs/
├── README.md                   # ce fichier : règles de la documentation (hors PDF)
├── .claude_doc.md              # plan et notes de Claude (hors PDF)
├── 01-<chapitre>/              # un dossier par chapitre, numéroté dans l'ordre de lecture
│   ├── index.md                #   ouverture du chapitre (le premier ouvre aussi le document)
│   └── <page>.md               #   une page par sujet
├── 02-<chapitre>/
│   ├── index.md
│   ├── <page>.md
│   └── decisions/              #   sous-dossiers permis (ex. ADR)
├── assets/                     # images et schémas, rangés par chapitre
├── site/                       # site de suivi tenu par Claude (hors PDF)
└── pdf/
    ├── page-de-garde.typ       # page de garde du PDF, en Typst (modifiable : couleurs, texte)
    └── <projet>.pdf            # PDF général généré par « genpdf »
```

### Palette de chapitres

Un point de départ pour construire le plan, pas une liste imposée : on ne garde que ce qui a du contenu,
on fusionne ce qui est maigre, on renomme selon le projet (« Utilisation », « API », « Matériel »…).

| Le lecteur veut…                                | Chapitre type        | Pages fréquentes |
|-------------------------------------------------|----------------------|------------------|
| Savoir ce qu'est le projet et à quoi il sert    | `presentation`       | glossaire |
| Réaliser une tâche, pas à pas                   | `guides`             | installation, utilisation |
| Comprendre comment c'est construit              | `architecture`       | fonctionnement, `decisions/` (ADR) |
| Trouver une option, une commande, un paramètre  | `reference`          | configuration, commandes, api |
| Déployer, sécuriser, dépanner                   | `exploitation`       | deploiement, securite, depannage |

Un petit projet peut tenir en deux chapitres ; un gros en avoir d'autres (`matériel`, `api`, `contribuer`…).
Un nouveau chapitre prend le numéro suivant ; on ne renumérote jamais les chapitres existants.

## Conventions

- **Noms :** minuscules, tirets, sans accents ni espaces (`guide-installation.md`).
- **Numéros :** `NN-` sur les dossiers de chapitre uniquement ; ils fixent l'ordre des chapitres dans le PDF.
- **`index.md` :** chaque chapitre en a un. C'est une **ouverture**, pas une page de contenu : titre, résumé,
  quelques lignes, puis un tableau qui lie chaque page du chapitre. **L'ordre des liens fixe l'ordre des pages dans le PDF**
  (les pages non liées viennent ensuite, par ordre alphabétique).
- **Ouverture du document :** l'`index.md` du premier chapitre dit ce qu'est le projet, à qui s'adresse la doc
  et par où commencer selon le besoin.
- **Titres :** un seul `#` par page (le titre), puis `##` et `###`. Le sommaire du PDF montre les chapitres et les titres de page.
- **Liens :** toujours relatifs (`../04-reference/commandes.md`). Dans le PDF, un lien vers une autre page devient du texte simple :
  son texte doit se suffire (« voir la page Commandes », pas « voir ici »).
- **Images :** dans `assets/<chapitre>/`, référencées en relatif, avec un texte alternatif. Une image introuvable fait échouer le PDF.
- **Schémas :** ASCII dans le Markdown quand c'est possible (lisible et comparable dans git) ; sinon une image SVG ou PNG dans `assets/`. Pas de Mermaid : le PDF ne saurait pas l'afficher.
- **Longueur :** chaque page commence une nouvelle feuille du PDF ; éviter les pages de quelques lignes (les fusionner).
- **Langue :** français. Les termes techniques courants restent en anglais (commit, branche, hook).

## Modèles

### Ouverture de chapitre (`index.md`)

```markdown
# Guides

> Les tâches courantes, pas à pas.

Une ou deux phrases pour situer le chapitre, si utile.

| Page | Pour |
|---|---|
| [Installation](installation.md) | installer le projet et ses dépendances |
| [Utilisation](utilisation.md) | les usages courants |
```

### Page

```markdown
# Titre de la page

> Résumé en une phrase : ce que la page apporte et à qui.

## Contexte
Pourquoi cette page existe.

## Contenu
Le cœur de la page.

## Voir aussi
- [Page liée](../04-reference/commandes.md) (seulement si utile)
```

### Page d'installation

Elle commence **toujours** par la liste simple de ce qu'il faut installer : un élément par ligne, le nom seul,
sans phrase ni commande. Le détail (paquets, commandes, réglages) vient ensuite, dans « Étapes ».

````markdown
# Installation

> Installer MagicTable et ses dépendances.

## À installer

- git
- python
- typst
- inter-font

## Étapes

### 1. Les paquets
```bash
sudo pacman -S git python typst inter-font
```

### 2. …

## Vérifier
Comment voir que l'installation a marché.
````

## Décisions d'architecture (ADR)

Chaque choix important (outil, structure, compromis) peut avoir sa fiche dans un sous-dossier `decisions/` du chapitre d'architecture,
numérotée dans l'ordre (`0001-choix-du-langage.md`). Une fiche n'est jamais réécrite :
si la décision change, on crée une nouvelle fiche qui remplace l'ancienne.

```markdown
# 0001 — Titre de la décision

- **Date :** AAAA-MM-JJ
- **Statut :** proposée | acceptée | remplacée par 000X

## Contexte
Le problème à résoudre.

## Décision
Ce qui a été choisi.

## Conséquences
Ce que ça implique, en bien comme en mal.
```

## Le PDF général

- Commande : `genpdf` à la racine du projet (ou `project pdf <projet>`) → `docs/pdf/<projet>.pdf`. Un premier PDF est généré à la création du projet.
- Contenu : la page de garde (`docs/pdf/page-de-garde.typ`, en [Typst](https://typst.app), police Inter : nom, résumé du `README.md`,
  version = dernier tag git sinon 0.1, date), puis un **sommaire** à deux niveaux (chapitres numérotés, pages),
  puis chaque chapitre : un bandeau « CHAPITRE NN » suivi de son `index.md`, puis ses pages, chacune sur une nouvelle feuille,
  avec un en-tête (projet, chapitre) et le numéro de page.
- Sans dossier de chapitre : la page de garde seule.
- La mise en page des chapitres est commune à tous les projets (dans `project`) ; seule la page de garde est propre au projet.
- Il est régénéré à chaque version publiée, et après chaque « rédige la doc » pour vérifier le rendu.
- On ne le modifie jamais directement : on corrige le `.md` (ou la page de garde), puis on régénère.

## Qui écrit la documentation

- Les pages de `docs/` sont écrites par l'utilisateur, ou par Claude **uniquement sur demande** (« rédige la doc »).
- Claude n'écrit seul que dans `.claude_doc.md` et `site/` (voir « Ce que Claude tient à côté de la doc »).

## Quand mettre la documentation à jour

- Un comportement change → la page concernée change dans le même commit (`docs:` si la doc seule change).
- Un choix important est fait → une nouvelle fiche ADR.
- Une nouvelle version est publiée → le PDF est régénéré.

La documentation du projet (`docs/`) est distincte du journal de travail avec Claude (`.claude/SESSION_LOG.md`).
