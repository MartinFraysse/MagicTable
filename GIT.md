# Git — aide-mémoire

Les commandes du quotidien pour ce projet (trunk-based : `main` + branches courtes).


## Commencer une tâche

```bash
git switch main
git pull
git switch -c feat/ma-tache
```

Types de branche : `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `ci`.


## Voir où on en est

```bash
git status          # fichiers modifiés
git diff            # détail des modifications
git log --oneline   # derniers commits
git branch          # branches locales
```


## Enregistrer son travail

```bash
git add <fichier>        # ou : git add .
git commit -m "feat(scope): description"
```


## Envoyer sur GitHub

```bash
git push -u origin feat/ma-tache    # la première fois
git push                            # les fois suivantes
```

Puis ouvrir la Pull Request sur GitHub → *Squash and merge*.


## Après le merge

```bash
git switch main
git pull
git branch -D feat/ma-tache
```


## Récupérer les nouveautés de `main` dans sa branche

```bash
git switch main
git pull
git switch feat/ma-tache
git merge main
```


## Annuler

```bash
git restore <fichier>            # annuler une modification pas encore ajoutée
git restore --staged <fichier>   # retirer un fichier du prochain commit
git commit --amend               # corriger le dernier commit (avant de l'avoir poussé)
```
