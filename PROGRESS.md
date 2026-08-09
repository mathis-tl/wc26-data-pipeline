# État du projet — wc26-data-pipeline

## Objectif du dernier sprint
Clarté du récit (revue éditoriale du BACKLOG) puis lancement de la Phase vitrine — page making-of technique, en ligne.

## Réalisations terminées
- **Revue éditoriale du narratif** (`index.astro`) : les 5 leviers du BACKLOG — modèle nommé (« régression de Poisson ») dès sa 1ʳᵉ mention ; maillon manquant *buts → probabilité de match* écrit en §Méthode (sous-section « D'un match à une probabilité ») pile là où la simulation le consomme ; glossaire complété (« proba de victoire », « proba de titre ») ; 4 renvois « plus bas » → ancres `#methode` ; aparté non vérifiable « Suisse/Paraguay » retiré. **BACKLOG éditorial = clos.**
- **Suites de la code-review** (0 bug de correctness, 3 nits faibles traités) : 6 `104` en dur → bindings `modelMeta.n_matches` / `metrics.matches_total` ; 3 règles de liens fusionnées en un idiome partagé.
- **Phase vitrine — page making-of `/coulisses`** (nouvelle) : ELT vs ETL, DuckDB vs Postgres, statique vs serveur, garde-fous qualité, « ce que je referais ». Charte du site, lien discret dans le footer, ancres du header rendues absolues (`/#analyse`). **Déployée en prod, vérifiée 200.**
- Ouverture de session : le dataviz non commité d'une session précédente (axes numériques, `table-layout: fixed`, paragraphe « 2026 en deux temps ») a été QA'é puis commité (`95dda5b`).
- **Fix géométrie timeline** (`EditionTimeline.astro`, `4d21056`) : la ligne « moyenne 3.06 » se dessinait ~11 px trop bas (référentiel `.edt__plot` — padding + rangée d'années — au lieu de `.edt__cols`), faisant passer la barre or 2026 (2.96) **au-dessus** de la moyenne, visuellement faux. Libellés d'années sortis dans leur propre rangée → base commune barres/ligne ; barre 2026 désormais ~5 px sous la ligne. Vérifié au pixel + captures desktop/mobile ; étiquette « 2.96 » ré-ancrée à droite (plus de rognage mobile).

## Fichiers impactés
- `dashboard/src/pages/coulisses.astro` (nouveau)
- `dashboard/src/pages/index.astro` (éditorial + bindings 104)
- `dashboard/src/components/SiteHeader.astro`, `SiteFooter.astro` (raccord nav + lien footer)
- `dashboard/src/components/{EditionTimeline,GroupTable,ScatterPlot,Takeaway,XgCurve}.astro` (dataviz, `95dda5b`)

## Décisions clés
- Revue édito faite **avant** la Phase vitrine (hors ordre « en tout dernier » du BACKLOG) — à ta demande explicite.
- Article publié comme **page du site Astro statique** (self-hosted, illustre la thèse « statique ») plutôt que plateforme externe.
- `104` → **bindings dynamiques** (pattern *compute-don't-assert* déjà en place pour `runnerUp`/`performanceRank`) pour ne jamais dériver au refresh cron nocturne.
- Commits éditorial (`docs`) et durcissement (`refactor`) **séparés par séquençage** (staging interactif indispo, tout dans un fichier).

## Validations effectuées
- `npm run build` : propre (2 pages : `/`, `/coulisses`).
- `scripts/shoot.mjs` desktop 1280 + mobile 390 sur `/` et `/coulisses` : **aucun débordement horizontal** ; captures ciblées (glossaire 6 items, formule 3 lignes, table de groupes, Fig. 6/xG) rendues correctes.
- `/code-review` (xhigh) : **0 bug de correctness**, 3 nits faibles — tous traités.
- Vérif HTML généré : **0 `104` en dur** restant en source, 6 bindings rendent bien « 104 » ; liens dédupliqués calculent `underline` + `--line-strong`.
- Déploiement Vercel prod : **READY** ; `dashboard-mathis7.vercel.app/coulisses` → **200**, contenu présent, lien footer `/coulisses` présent en prod.

## Risques / points ouverts
- `deploy.yml` existe mais le déploiement reste lancé à la main : à clarifier (workflow mort ou à brancher pour l'auto-deploy Git↔Vercel).
- `upsets.json` toujours sans contrat d'export ; crédits photos « à compléter » dans le footer (`SiteFooter.astro:31` ; nom = `SITE.author` dans `lib/site.ts`).
- Article **en ligne** mais promotion (post LinkedIn / lien CV) = part humaine, non faite.

## Prochaine étape exacte
`origin/main` réaligné sur la prod (push des 5 commits incl. le fix géométrie) et prod redéployée ce tour. Reprendre la Phase vitrine par le polish du `README` au niveau recruteur.
