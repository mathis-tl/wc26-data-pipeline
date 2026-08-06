# État du projet — wc26-data-pipeline

## Objectif du dernier sprint
Accompagner le lecteur du dashboard et refermer le récit (Tier 1 + 2 du plan `docs/NEXT_SESSION.md`).

## Réalisations terminées
> ⚠️ En code, **build vérifié, mais PAS encore commité ni déployé** (working tree).
- **Tier 1.1 — pédagogie des métriques** : composant `<Term>` (tooltips), encadré « Comment lire ce rapport », rangs inline dans le tableau de notes (piège d'échelle désamorcé : Espagne Att. #6 / Déf. #1).
- **Tier 1.2 — KPIs contextualisés** : ligne de contexte sous chaque KPI, dérivée de `mart_edition_comparison` (+40 vs 2022, record de buts, 1ʳᵉ à 48, plus haut depuis 1958).
- **Tier 1.3 — clôture éditoriale** : section « Ce que la machine retient » (place de l'Espagne, verdict, 3 records).
- **Tier 2.4 — « À retenir »** sous chaque figure annexe (6 lignes, chiffres réels).
- **Tier 2.5 — ScatterPlot** : anti-collision des labels + outliers labellisés (ENG meilleure attaque, GER pire défense) + leader lines.
- **Tier 2.6 — réconciliation des 2 sources** : diagramme `SourceMatch.astro` (SofaScore↔football-data, matching chronologique strict 8/8).
- **Tier 3 — PipelineDiagram** nomme les 2 sources + l'étape de réconciliation.

## Fichiers impactés
- Nouveaux : `dashboard/src/components/{Term,Takeaway,SourceMatch}.astro`
- Modifiés : `dashboard/src/pages/index.astro`, `components/ScatterPlot.astro`, `components/PipelineDiagram.astro`
- Kit workflow : `.claude/`, `CLAUDE.md`, `PROGRESS.md`, `.git/hooks/post-commit`, `setup-claude.sh`

## Décisions clés
- Kit de sprints adopté (voir `CLAUDE.md`), version **non destructive** et réutilisable (`setup-claude.sh`) : merge de `settings.json`, `/gquery` CLI-ou-skill, ré-indexation **incrémentale** seulement.
- Corrigé un chiffre faux du plan : « +28 vs 2022 » → **+40** (104 vs 64 matchs), dérivé du mart, jamais en dur.
- Rejeté (assumé dans les limites) : analytics joueurs (per-90, PPDA, radars) — pas de donnée événementielle par joueur.

## Validations effectuées
- `npm run build` (astro) : OK, 1 page générée, aucune erreur.
- Inspection du HTML compilé (`dist/index.html`) : KPIs, tooltips, rangs table, epilogue, takeaways, source-match — tous rendus corrects.
- graphify : carte régénérée (361 nœuds / 547 arêtes / 33 communautés, AST-only).

## Risques / points ouverts
- QA visuelle (`shoot.mjs` desktop+mobile) **pas encore relancée** sur les nouveaux éléments.
- 75 arêtes « dangling » dans la carte (imports vers JSON/CSS/fonts sans nœud code) — attendu, pas une régression.
- Lignage dbt `ref()` invisible dans la carte (limite AST connue).

## Prochaine étape exacte
**Sprint 1** : QA visuelle (`shoot.mjs`) → commits atomiques → push → `cd dashboard && npx vercel --prod --yes` → vérifier 200 + contenu live sur https://dashboard-mathis7.vercel.app.
