# Règles du site de suivi (`docs/site/`)

## À quoi il sert

Montrer à l'utilisateur, sur des pages claires avec couleurs et schémas, **ce que Claude propose et ce qu'il a fait**,
sujet par sujet, et **comment le projet est construit**. C'est le fil de travail, pour comprendre les enjeux sans lire le terminal.
Ce n'est pas la doc finale (pages `docs/NN-*/` et le PDF) : celle-ci est préparée dans `docs/.claude_doc.md` (voir `regles-doc.md`).

## Les pages

| Fichier | Contenu | Mis à jour |
|---|---|---|
| `index.html` | Le projet en un schéma + la liste des sujets, le plus récent en haut, avec statut et date | à chaque sujet créé ou changé de statut |
| `construction.html` | Le projet **tel qu'il est** : vue d'ensemble, parties, fichiers maîtres, technos | après chaque sujet réalisé |
| `sujets/AAAA-MM-JJ-titre-court.html` | Une page par sujet, copiée de `sujets/_modele.html` | à chaque étape du sujet |
| `style.css` | Le style commun (sombre, clair si le navigateur le demande) | rarement ; pas de style dans les pages |

Nom d'un sujet : date du jour + titre court en minuscules, tirets, sans accents (`2026-11-20-mode-hors-ligne.html`).

## Le déroulé d'un sujet

| Étape | Statut (classe `.pill`) | Parties de la page |
|---|---|---|
| 1. Une demande implique un choix ou un changement | `propose` | **Le besoin** ; **Ce que je propose** : 2 ou 3 options (ce que chacune apporte `+` et coûte `−`), le choix de Claude en une phrase, un schéma si ça aide. **Puis attendre la décision.** |
| 2. Décision reçue | `en-cours` | **Décision** : l'option retenue et la date. Réalisation. |
| 3. Réalisé | `fait` | **Ce que j'ai fait** : tableau des fichiers touchés, schéma du fonctionnement, ce qui a été vérifié ou non. Puis `construction.html`. |
| Option écartée | `abandonne` | Une phrase pour dire pourquoi. |
| Limites, suites | — | **À savoir**, seulement s'il y a quelque chose. |

Pas de page pour une simple question, une explication ou une correction évidente (faute, petit bug sans choix) :
la correction est faite directement, puis notée dans « Ce que j'ai fait » du sujet concerné, ou dans `construction.html` si elle change l'état du projet.

## Comment écrire

- Peu de texte : phrases courtes, une idée par phrase. Tableaux et schémas plutôt que paragraphes.
- Schémas en SVG dans la page, avec les classes de `style.css` : `.box`, `.box-a`, `.box-c`, `.box-ok`, `.box-w`
  (boîtes), `.arrow` (flèches, garder le `<defs>` du marqueur `fleche`), `.t` (titre), `.sub` (sous-titre).
- Garder la structure du modèle : barre de navigation, en-tête `.hero`, parties `.sec` dans l'ordre.
- `index.html` : un `<li>` par sujet ; au premier sujet, supprimer le paragraphe `.vide`.
- Les liens entre pages sont relatifs (`../index.html` depuis `sujets/`).

## Dans le terminal

À chaque mise à jour du site, **une ligne**, le détail étant sur la page :

```
🌐 site : je propose — <titre> → docs/site/sujets/<fichier>.html
```

Autres verbes : `fait`, `mis à jour`, `abandonné`. L'utilisateur ouvre le site avec `project site <nom>` et rafraîchit (F5).
