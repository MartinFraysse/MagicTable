# CLAUDE.md — MagicTable

## Principes

- Répondre en français, explicite et concis, sans phrase d'introduction.
- **Proposer avant de réaliser** : tout ce qui demande un choix (fonctionnalité, structure, dépendance, techno)
  est d'abord proposé sur le site de suivi. Une fois la décision donnée, réaliser sans redemander à chaque étape.
- Demande floue → poser une question plutôt que deviner.
- Après une modification, vérifier (lancer, tester, linter) et dire honnêtement ce qui a été vérifié ou non.

## Comment travailler

```
Demande → page sujet « Proposé » sur le site → décision de l'utilisateur → réalisation → page « Fait »
```

1. Une demande qui implique un choix ou un changement : page sujet sur le site (règles : `.claude/regles-site.md`), puis **attendre la décision**.
2. Décision reçue : réaliser, en changements minimaux et incrémentaux, sans refactor ni dépendance non proposés.
3. Réalisé : compléter la page sujet, mettre à jour `construction.html`, les notes de doc si utile, puis le journal.

Pas de page pour une simple question, une explication ou une correction évidente (faute, petit bug sans choix) :
la corriger directement, puis la noter sur le site.

## Qui écrit quoi

| Fichier | Claude écrit seul ? | Quand |
|---|---|---|
| `docs/site/` | oui | à chaque étape d'un sujet (`.claude/regles-site.md`) |
| `docs/.claude_doc.md` | oui (le plan : après validation) | dès qu'il apprend quelque chose d'utile pour la doc finale (`.claude/regles-doc.md`) |
| `.claude/SESSION_LOG.md` | oui | après chaque tâche significative (voir « Journal ») |
| `README.md`, section « Organisation du dépôt » | oui | quand un fichier ou dossier est ajouté, déplacé ou supprimé (arbre et commentaires seulement) |
| `src/README.md` | oui, sans sortir du modèle | quand `src/` évolue ; une idée hors modèle va dans « Idée d'ajout » |
| `src/` (le code) | oui, après décision | sujet accepté, ou correction évidente |
| `README.md` (le reste), pages `docs/NN-*/` | **sur demande seulement** | « rédige la doc » : procédure de `.claude/regles-doc.md` ; si un changement les rend faux, le noter dans `docs/.claude_doc.md` |
| Nouveau fichier à la racine | **sur accord** | la racine reste propre : le code dans `src/`, la doc dans `docs/` |

## Code

- Environnement : Arch Linux. Préférer Bash, Python et les outils POSIX.
- Respecter la structure et le style existants (`.editorconfig`).

## Sécurité

- Jamais de secret en clair (mot de passe, token, clé) dans le code, les commits, le site ou les notes.
- Les secrets vont dans `.env`, ignoré par git ; `.env.example` liste les variables sans leurs valeurs.
- Valider les entrées externes ; signaler toute faille repérée, même hors sujet.

## Git (trunk-based, voir `README.md` et `GIT.md`)

- Aucune commande git sans demande explicite.
- Jamais de commit direct sur `main` : proposer une branche courte `<type>/<description>`.
- Messages Conventional Commits : `<type>(<scope>): <description>`.
- Ne jamais réécrire l'historique ni forcer un push sans accord.

## Les trois fichiers vivants

| Fichier | Pour qui, pour quoi | Décrit |
|---|---|---|
| `docs/site/` | l'utilisateur : comprendre ce que Claude propose et fait, avec des schémas | les sujets et le projet tel qu'il est |
| `docs/.claude_doc.md` | la doc finale : sa matière première | le présent, en texte prêt à reprendre |
| `.claude/SESSION_LOG.md` | reprendre le travail d'une session à l'autre | l'historique, daté |

Une information n'est écrite qu'à un endroit : les autres y renvoient par un lien.

## Journal de session (`.claude/SESSION_LOG.md`)

**Au démarrage**, le hook `SessionStart` (`.claude/hooks/journal.sh`) donne le journal. Première réponse : un résumé court,
en phrases, une idée par phrase, une ligne vide entre les phrases, et une seule question à la fin :

```
**📍 Dernière session — AAAA-MM-JJ · <titre>**

**✅ Fait**
<phrases ; petit schéma ASCII (≤ 10 lignes) seulement s'il aide>

**🔜 Prochaines étapes**
<phrases, la prioritaire en premier>

**⚠️ Points ouverts** (seulement s'il y en a)
<phrases>

**🧰 Commandes** · `genpdf` PDF de la doc · `project site MagicTable` site de suivi · `init-git` / `remove-git` dépôt GitHub
```

**Premier démarrage** (juste après `project create`) : pas de résumé ; présenter le projet en une phrase,
le bloc 🧰 Commandes ci-dessus, et demander par quoi commencer.

Après `/clear` ou un résumé automatique de la conversation, le journal est redonné pour contexte : ne pas refaire le résumé.

**Après chaque tâche significative**, sans demander :
- en haut de « Historique », une entrée `### AAAA-MM-JJ — titre` (ou compléter celle du jour) : une idée par puce
  (fait, fichiers touchés, décisions avec lien vers la page sujet, problèmes ouverts) ;
- tenir à jour « Prochaines étapes » ;
- au-delà d'environ 15 entrées, condenser les plus anciennes dans « Archives ».

## En fin de réponse

Une ligne par fichier vivant mis à jour, rien de plus (le journal n'est pas annoncé) :

```
🌐 site : je propose — <titre> → docs/site/sujets/<fichier>.html
📝 doc : <ce qui a été ajouté ou corrigé> → docs/.claude_doc.md
```

## Règles détaillées

@regles-site.md
@regles-doc.md
