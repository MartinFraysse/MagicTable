# Journal de sessions — MagicTable

> Fichier de persistance entre les sessions Claude Code.
> Lu automatiquement au démarrage (hook `SessionStart`) et mis à jour par Claude après chaque tâche significative.
> Entrées les plus récentes en haut, une idée par puce.

## 🔜 Prochaines étapes
- Corriger les écarts relevés en rédigeant la doc (voir « À savoir » du [sujet](../docs/site/sujets/2026-11-20-plan-de-la-documentation.html)) : boutons Archiver/Exporter du Dashboard, chrono non mémorisé, texte de Paramètres › Notation, « Terminer » à côté de « Lancer le bracket ».
- `regular_players.json` n'est plus suivi, mais reste dans l'historique git public : le purger demanderait de réécrire l'historique (à décider).
- `dashboard_view_main.py` (~1 000 lignes, une seule classe) reste à découper : à proposer avec des tests d'interface.

## 🗓️ Historique

### 2026-11-20 — Release v1.7.0
- Branche `chore/release-1.7.0` → PR (squash) → tag `v1.7.0` → CI build Windows + release GitHub.
- `fpdf2` ajouté (requirements, `.spec`) ; export PDF réparé sans police Unicode (filtre d'emojis élargi + repli latin-1) ; `tests/test_pdf_export.py`.
- `src/version.py` → 1.7.0 ; `CHANGELOG.md` rédigé.
- `src/data/regular_players.json` retiré du suivi git (données personnelles, dépôt public) et ignoré.
- Données locales (`tournaments.json`, `commanders.json`, une image) laissées hors des commits.
- Vérifié : 47 tests, pyflakes, build PyInstaller local (binaire démarre, `fpdf` et `networkx` embarqués).

### 2026-11-20 — Documentation Markdown
- Plan A validé (5 chapitres) puis rédigé : `docs/01-presentation` à `docs/05-exploitation`, 16 pages + 3 ADR ([sujet](../docs/site/sujets/2026-11-20-plan-de-la-documentation.html)).
- PDF régénéré (`genpdf`, 40 pages) et relu en image ; schémas ASCII limités à 76 caractères.
- `docs/technical-doc.md` et `docs/architecture.md` supprimés (repris) ; notes de doc vidées ; README et `construction.html` à jour.
- Écarts de l'appli relevés, non corrigés : `fpdf2` absent de requirements, boutons Archiver/Exporter jamais affichés, chrono non mémorisé, texte Paramètres › Notation faux.

### 2026-11-20 — Nettoyage, Swiss optimal, mise au format du modèle
- Projet mis au format du modèle `~/Documents/projets/.template` : `.claude/` (CLAUDE.md, règles, hook journal), `GIT.md`, `.env.example`, `docs/` (README, notes, site, page de garde), `.gitignore` fusionné ; `README.md` recomposé (sections de l'appli conservées) ; `.claude/rules.md`, `docs/COMMITS.md` (ancien modèle) supprimés ; `TECHNICAL_DOC.md` → `docs/technical-doc.md`, `docs/ARCHITECTURE.md` → `docs/architecture.md` ([sujet](../docs/site/sujets/2026-11-20-mise-au-format-du-modele.html)).
- Bot Discord et synchro serveur supprimés : app 100 % locale (`discord_bot/`, `src/sync/` retirés).
- Nettoyage : classement final, barème et formats centralisés (`core/ranking.py`, `core/formats.py`, `core/commander_stats.py`) ; code mort retiré ; `launch_view`, `commander_stats`, `historic_view` découpés.
- Corrections : bracket (seed 1 vainqueur sans jouer si effectif réduit), bye « consommé » après régénération, stats joueurs réguliers (source unique : archives, lien explicite ou pseudo), podium du PDF.
- Swiss réécrit (`core/swiss_pairing.py`) : couplage de poids minimal (networkx) ; corrige le round 1 alphabétique, les gros écarts de points, les gels de 1 à 4,5 s ; Swiss imposé à tous les formats 1v1 ; bye = 2-0 dans le GW% ; rondes marquées terminées.
- Nouvelle dépendance `networkx` (requirements.txt, MagicTable.spec), installée dans `.venv`.
- Tests : 43 (dont `tests/test_swiss.py`, `tests/test_core_rules.py`) ; pyflakes propre.
- Ouvert : rien de commité ; `dashboard_view_main.py` non découpé.

### 2026-11-20 — Création du projet
- Projet mis au format du modèle (équivalent de `project create`) sur le dépôt MagicTable existant.

## 📦 Archives

<!-- Les entrées les plus anciennes, condensées (une ligne par entrée) quand l'Historique dépasse ~15 entrées. -->
