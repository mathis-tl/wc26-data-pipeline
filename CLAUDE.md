# wc26-data-pipeline — règles projet & workflow

<!-- CLAUDE-KIT:START (bloc géré par setup-claude.sh — édite entre les marqueurs) -->
## Langue
- Réponds en **français**. Les messages de commit restent en **anglais** (conventional commits, non négociable).

## Workflow par micro-sprints
- Reprise de session : `/sprint-start`. Clôture : `/sprint-end` puis `/clear`.
- Explorer l'architecture / les dépendances : `/gquery "<question>"` — jamais `cat graphify-out/graph.json`.
- Revue avant commit : `/review-change` (→ `/code-review`).
- Point de contrôle : `/context-health`.

## Graphify
- Ne lance **jamais** une ré-indexation complète (`graphify .`) de ta propre initiative.
- La carte se met à jour en **incrémental** : hook git `post-commit` + `graphify update .` au `/sprint-end`.
- Pour comprendre le code, interroge la carte (`graphify query` / `/gquery`), pas le JSON brut.

## Discipline de contexte & garde-fous
- Un seul objectif par sprint. Session longue → `/compact` ; objectif atteint ou sujet qui change → `/sprint-end` + `/clear`.
- Ne prétends jamais qu'un test/commande a tourné sans l'avoir réellement exécuté.
- Commit, push, déploiement, migration destructive : uniquement sur demande explicite.
- `PROGRESS.md` = état vivant et court du sprint. `SESSION_NOTES.md` = archive longue.
<!-- CLAUDE-KIT:END -->
