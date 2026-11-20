# 0001 — Application 100 % locale

> Pourquoi MagicTable n'a plus ni serveur ni bot Discord.

- **Date :** 2026-11-20
- **Statut :** acceptée

## Contexte

MagicTable synchronisait ses données avec un serveur (API FastAPI) partagé avec un bot Discord.
Le bot créait des salons par tournoi, publiait les appariements et laissait les joueurs saisir leurs résultats (`!score`).

Ce fonctionnement posait plusieurs problèmes :

- deux écrivains (l'application et le bot) sans versionnage : des résultats et des inscriptions pouvaient être écrasés ;
- chaque lecture de fichier attendait le serveur (jusqu'à 2 s), ce qui figeait l'interface ;
- un serveur et un bot à héberger et à maintenir, avec une clé d'API et des données personnelles exposées.

## Décision

Supprimer le bot Discord, l'API et toute la synchronisation. Les données sont des fichiers JSON locaux,
lus et écrits uniquement par l'application.

## Conséquences

- Plus de pertes de données ni de gels liés au réseau ; plus rien à héberger.
- Les joueurs ne saisissent plus leurs résultats depuis Discord : l'organisateur les saisit dans l'application.
- Plus de partage automatique des données entre plusieurs ordinateurs : pour changer de poste, copier le dossier de données.
- Seule connexion restante : la vérification des mises à jour sur GitHub.
