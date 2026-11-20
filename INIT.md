# Initialisation d'un projet

Aide-mémoire pour démarrer un nouveau projet à partir du template.


## 1. Créer le projet

```bash
project create <nom>        # ou Super + P → Nouveau projet
```

Copie ce modèle dans `~/Documents/projets/<nom>`, met le nom du projet partout, écrit la première entrée du journal,
génère la page de garde du PDF (`docs/pdf/<nom>.pdf`), puis ouvre le projet : Claude présente alors les commandes du projet.
Git et GitHub ne sont pas créés : voir section 4.


## 2. Ouvrir et suivre le projet

| Commande | Effet |
|---|---|
| `project <nom>` (ou `Super + P`) | VS Code à gauche, Claude en haut à droite (résumé de la dernière session), un terminal en bas à droite, sur le premier workspace vide de l'écran |
| `project site <nom>` | Ouvre le site de suivi : ce que Claude propose et ce qu'il a fait (F5 pour les nouveautés) |
| `genpdf` (à la racine du projet) | Régénère le PDF de la doc (comme `project pdf <nom>`) |
| `project` | Liste les projets et leur état git |


## 3. Remplir le minimum

- `README.md` : le résumé du projet en une ligne, sous le titre (il apparaît aussi sur la page de garde du PDF).
- `src/README.md` : le résumé et la stack, dès qu'on les connaît.


## 4. Créer le dépôt git

**En une commande**, à la racine du projet :

```bash
init-git
```

Elle fait les sections 4 et 5 ci-dessous (c'est l'inverse de `remove-git`, section 6) : montre les fichiers du premier commit, demande confirmation, crée le dépôt GitHub **privé**, pousse, règle le merge et tente la protection de `main`. Le détail ci-dessous sert à comprendre ou à le faire à la main.

**À la main :**

Depuis le dossier du projet :

```bash
git init -b main
git add .
git commit -m "chore: initial project structure"
gh repo create <nom> --private --source=. --remote=origin --push
```

- `git init -b main` : transforme le dossier en dépôt git, avec `main` comme branche principale.
- `git add .` : prépare tous les fichiers pour le premier commit.
- `git commit -m "…"` : enregistre ce premier état du projet.
- `gh repo create <nom> --private` : crée le dépôt privé sur GitHub.
- `--source=.` : utilise le dossier courant comme contenu du dépôt.
- `--remote=origin` : relie le dossier local au dépôt GitHub sous le nom `origin`.
- `--push` : envoie tout de suite le premier commit sur GitHub.

> ⚠️ Avant le `git add .`, jeter un œil à `.gitignore` : il ignore déjà `.env`, les clés et les fichiers
> propres à l'éditeur, mais c'est le moment d'y ajouter ce qui est propre au projet.


## 5. Protéger `main` sur GitHub

À lancer depuis le dossier du projet.

**Merge : squash uniquement, branche supprimée après le merge**

```bash
gh repo edit --enable-squash-merge --enable-merge-commit=false --enable-rebase-merge=false --delete-branch-on-merge
```

- `--enable-squash-merge` : une PR = un seul commit propre sur `main`.
- `--enable-merge-commit=false` : pas de commit de merge qui encombre l'historique.
- `--enable-rebase-merge=false` : pas de copie de tous les petits commits de la branche.
- `--delete-branch-on-merge` : la branche disparaît de GitHub une fois fusionnée.

**Pull Request obligatoire sur `main`, pour tout le monde**

```bash
gh api -X PUT "repos/{owner}/{repo}/branches/main/protection" --input - <<'JSON'
{
  "required_status_checks": null,
  "enforce_admins": true,
  "required_pull_request_reviews": { "required_approving_review_count": 0 },
  "restrictions": null
}
JSON
```

- `gh api -X PUT` : envoie une requête à l'API GitHub pour **définir** un réglage.
- `repos/{owner}/{repo}/branches/main/protection` : le réglage visé, la protection de `main` ; `gh` remplit `{owner}` et `{repo}` avec le dépôt du dossier courant.
- `--input - <<'JSON' … JSON` : le texte entre les deux `JSON` est envoyé comme contenu de la requête.
- `"required_status_checks": null` : aucun test automatique (CI) exigé avant le merge.
- `"enforce_admins": true` : la règle s'applique aussi au propriétaire du dépôt.
- `"required_approving_review_count": 0` : PR obligatoire, mais sans approbation (on peut fusionner sa propre PR).
- `"restrictions": null` : pas de liste de personnes autorisées à fusionner.

> ⚠️ Selon le compte, GitHub peut refuser la protection d'un dépôt privé (« Upgrade to GitHub Pro ») :
> `init-git` le signale par un avertissement. Seule la première commande s'applique alors,
> et ne pas pousser sur `main` reste une discipline personnelle.


## 6. Supprimer

| Commande | Effet |
|---|---|
| `remove-git` (à la racine du projet) | Supprime le dépôt GitHub **et** le `.git` local ; les fichiers restent. Nom du projet à taper |
| `project remove <nom>` | Supprime le dossier du projet ; s'il a un dépôt GitHub, propose aussi de le supprimer (via `remove-git`) |
| `project detach <nom>` | Retire seulement le `.git` local, sans toucher à GitHub |

La première suppression d'un dépôt GitHub demande d'accorder à `gh` le droit `delete_repo` : `remove-git` le propose (une seule fois).


## 7. Commencer à travailler

Première branche, puis le cycle habituel : voir `GIT.md`.
