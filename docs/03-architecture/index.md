# Architecture

> Comment MagicTable est construit : ses couches, ses algorithmes et les choix qui les expliquent.

Ce chapitre s'adresse à qui veut lire ou modifier le code (`src/`).
La première page donne la carte d'ensemble, la deuxième détaille les règles de calcul,
les fiches de décision gardent le « pourquoi » des choix importants.

| Page | Pour |
|---|---|
| [Fonctionnement](fonctionnement.md) | les couches, les modules et le déroulé d'un tournoi dans le code |
| [Appariements et classements](appariements-et-classements.md) | le Swiss, les tables Commander, les standings, le bracket et le classement final |
| [0001 — Application 100 % locale](decisions/0001-application-locale.md) | pourquoi il n'y a ni serveur ni bot Discord |
| [0002 — Swiss par couplage optimal](decisions/0002-swiss-couplage-optimal.md) | pourquoi le Swiss s'appuie sur networkx |
| [0003 — Statistiques calculées depuis les archives](decisions/0003-stats-depuis-les-archives.md) | pourquoi aucun compteur n'est stocké |
