Reprends le sprint en cours sans recharger tout l'historique.

1. Lis `PROGRESS.md` s'il existe (état du dernier sprint).
2. Exécute `git status --short` puis `git log --oneline -5`.
3. Si `graphify-out/graph.json` existe, note simplement la présence de la carte — **ne la régénère pas**.
4. Présente une synthèse courte en 3 puces :
   - Ce qui a été accompli au dernier sprint.
   - État Git actuel (branche, fichiers modifiés).
   - La tâche prioritaire de cette session (« Prochaine étape » de PROGRESS.md).

Attends ma validation de l'objectif avant d'écrire du code.
