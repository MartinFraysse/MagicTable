# Changelog

## [1.7.0] — 2026-11-20

### Changé
- **Appariement Swiss réécrit** : chaque ronde est l'appariement optimal (couplage de poids minimal).
  Ronde 1 tirée au sort (elle était alphabétique), écarts de points minimaux, plus de gel au-delà de 25 joueurs.
- Swiss appliqué à tous les formats 1v1 ; le Commander multi garde ses tables de 3-4.
- Statistiques des joueurs réguliers calculées uniquement depuis les tournois archivés : mêmes chiffres partout.
- Un bye compte comme une victoire 2-0 dans le GW%.
- Export PDF : podium selon le vrai classement final ; fonctionne sans police Unicode (Windows).

### Corrigé
- Phase finale : un joueur ne gagne plus un match dont l'adversaire n'est pas encore connu (effectif réduit, abandon).
- Bye « consommé » à tort après la régénération d'une ronde.
- « Ajouter aux joueurs permanents » depuis le classement relie maintenant le joueur à sa fiche.
- Erreur à la fermeture de l'application.

### Retiré
- Bot Discord et synchronisation serveur : l'application est 100 % locale.

### Technique
- Nouvelles dépendances : `networkx`, `fpdf2` (désormais embarqué dans l'exécutable).
- Code nettoyé : classement final, barème et formats centralisés dans `core/`.
- Documentation complète dans `docs/` (5 chapitres, PDF) ; structure de projet mise au format du modèle.
- Tests : standings, Swiss, bracket, statistiques, export PDF.

## [1.6.6] et antérieures

Voir l'historique git et les releases GitHub.
