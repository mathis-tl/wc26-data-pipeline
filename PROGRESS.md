# État du projet — wc26-data-pipeline

## Objectif du dernier sprint
Sprint 1 — accompagner le lecteur du dashboard et refermer le récit (Tier 1+2+3 de `docs/NEXT_SESSION.md`), puis livrer.

## Réalisations terminées
> ✅ **Livré et déployé** — https://dashboard-mathis7.vercel.app (HTTP 200 vérifié, contenu présent en live).
- **Tier 1.1** pédagogie : `<Term>` (tooltips), encadré « Comment lire ce rapport », rangs inline table (Espagne Att. #6 / Déf. #1) + légende qui nomme le piège d'échelle.
- **Tier 1.2** KPIs contextualisés, dérivés de `mart_edition_comparison` (+40 vs 2022, record de buts, 1ʳᵉ à 48, plus haut depuis 1958). Chiffre faux du plan corrigé (+28 → +40).
- **Tier 1.3** clôture éditoriale « Ce que la machine retient » (place de l'Espagne, verdict, 3 records).
- **Tier 2.4** « À retenir » sous chaque figure annexe (6, chiffres réels).
- **Tier 2.5** ScatterPlot : anti-collision + outliers (ENG/GER) + leader lines.
- **Tier 2.6** diagramme `SourceMatch` (réconciliation 2 sources, matching chrono strict 8/8).
- **Tier 3** PipelineDiagram nomme les 2 sources + l'étape de réconciliation.
- **Kit sprints** installé (`.claude/`, `CLAUDE.md`, `PROGRESS.md`, hook git incrémental, `setup-claude.sh` réutilisable).

## Fichiers impactés
- Nouveaux composants : `dashboard/src/components/{Term,Takeaway,SourceMatch}.astro`
- Modifiés : `dashboard/src/pages/index.astro`, `components/{ScatterPlot,PipelineDiagram}.astro`
- Kit : `.claude/`, `CLAUDE.md`, `setup-claude.sh`, `.gitignore`

## Décisions clés
- Livraison direct-to-main (bypass admin de la règle PR) + `npx vercel --prod`, comme le reste de la phase 3.
- Kit adopté en version non destructive/réutilisable ; graphify = CLI **et** skill ici, ré-indexation incrémentale seulement.
- Rejeté/assumé : analytics joueurs (pas de donnée événementielle par joueur).

## Validations effectuées
- `npm run build` : OK. QA `shoot.mjs` : desktop 1280 OK, mobile **390=390 aucun débordement** (bug tooltip `display:none` corrigé).
- HTML compilé + live vérifiés : table #6/#1, KPI, epilogue, source-match, takeaways.
- 3 commits atomiques, rebase sur le commit data du cron (#30), push, deploy, HTTP 200.
- graphify : carte régénérée (361 nœuds / 547 arêtes / 33 communautés).

## Risques / points ouverts
- Dette de fond inchangée : crédits photos du footer, intégration Vercel↔Git (redeploy manuel), lignage dbt `ref()` invisible dans la carte.
- Tier 3 optionnel restant : glossaire complet repliable en bas de la section méthode (non fait, faible priorité).

## Prochaine étape exacte
Au choix : (a) glossaire repliable en bas de « Méthode » (Tier 3 restant), ou (b) brancher l'intégration Vercel↔Git pour un redeploy auto sur push. Sinon, nouveau sujet.
