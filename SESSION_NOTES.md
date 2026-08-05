# SESSION_NOTES

## Session 2026-08-05 (après-midi) — durcissement « niveau senior » du pipeline ✅

Objectif fixé par Mathis : le dashboard visuel est bon, mais « on veut que ça claque niveau pipeline aussi, la plus haute qualité possible — je suis sûr qu'on est loin d'un niveau senior ». Dix chantiers, chacun son commit atomique, tous shippés sur `main`, CI verte, déployé en prod. La passe visuelle/centrage du dashboard (même journée, plus tôt) est distincte.

### Fait

- **A · Socle outillage.** Ruff élargi de E/F par défaut à `I,B,UP,SIM,RUF` ; `ruff format` adopté ; Pyright (standard) sur ingestion/analytics/tests/export ; pre-commit qui reflète la chaîne via uv. CI : lint + format-check + type-check avant les tests. Les nouvelles règles ont révélé de **vrais bugs** — un `zip` qui tronquait en silence (désormais `strict=True`, car cet alignement EST l'invariant de réconciliation SofaScore↔modèle), une closure à variable de boucle non liée, une assertion de test sur `Exception` aveugle.
- **B · Contrats de schéma à la frontière d'ingestion** (`ingestion/schemas.py`). Chaque dataset brut déclare ses champs cœur (types + nullabilité). Politique de dérive : champs inconnus acceptés et loggés ; champ cœur manquant ou retypé → lève avant toute écriture. Un test valide l'archive réelle commitée contre ses propres contrats.
- **C · Durcissement dbt.** Contrats enforced sur les (désormais 5) marts ; `dbt source freshness` (warn 26h/error 48h) qui attrape la péremption silencieuse que les row-counts ratent ; paramètres d'édition (matchs/équipes/buteurs/fenêtre) en vars dbt ; test singulier de fenêtre de tournoi ; tous les kwargs de tests génériques migrés vers la propriété `arguments:` de dbt 1.10 — build sans deprecation.
- **D · Correction analytics.** Le `fit()` Poisson refuse désormais de renvoyer des notes issues d'un optimiseur non convergé (il ne vérifiait jamais `res.success` — un solve échoué aurait shippé des valeurs plausibles mais fausses) et rejette les entrées dégénérées ; métadonnées de convergence (NLL final, lignes utilisées) exportées dans `model_meta.json`. 13 tests modèle/simulation (cas limites du bracket, invariants de progression).
- **E · Observabilité des runs** (`ingestion/ops.py`). Chaque étape append dans `data/ops/runs.jsonl` (append-only dans git, car le fichier DuckDB est amnésique entre runs CI). L'export dérive le bilan opérationnel ; la status line affiche « runs N/N ». Vide jusqu'au premier vrai run cron — aucun chiffre semé.
- **F · Tests de contrat sur le JSON exporté.** Le build Astro importe le JSON statiquement → une rupture de forme rend `undefined` au lieu d'échouer. 19 tests figent la forme de chaque fichier importé, + un méta-test qui grep les sources et échoue si le front importe un export sans contrat.
- **G · ADRs** (`docs/adr/`). Cinq décisions avec alternatives rejetées et compromis : raw versionné, dbt-duckdb, classements recalculés, buts attendus modélisés (jamais « xG »), défenses aux frontières.
- **H · Auto-déploiement + dbt docs publiées.** `deploy.yml` redéploie sur Vercel à chaque push sur `main` touchant `dashboard/**` (gardé, skip proprement tant que le owner n'a pas ajouté `VERCEL_TOKEN` + vars org/projet). `dbt docs generate --static` produit un explorateur lineage/modèles/tests autonome servi à `/dbt-docs`, lié dans le footer, régénéré dans le workflow quotidien.
- **I · One-off SofaScore nettoyé.** Suppression du handoff `/tmp` fragile ; id d'équipe Espagne épinglé en constante vérifiée avec garde ; garde de re-run pour qu'une invocation accidentelle ne brûle pas le quota 50 req/mois (`--force` pour forcer).
- **J · Backfill historique — 2026 en contexte.** Seed dbt de chaque Coupe du Monde masculine 1930–2022 (jfjelstul/worldcup, buts/match calculés depuis les vrais scores, recroisés avec les chiffres connus). `mart_edition_comparison` unionne l'histoire avec 2026 calculé en direct depuis `fct_matches` de façon identique. Nouveau bloc dashboard « 2026 dans l'histoire » : timeline en colonnes des buts/match sur les 23 éditions, 2026 en or au-dessus de la moyenne historique — **7ᵉ sur 23, la Coupe du Monde la plus prolifique depuis 1958**, 100 % dérivé de la donnée.
- **Bonus.** Vrai écart de reproductibilité corrigé : DuckDB ne garantit aucun ordre de lignes sans `ORDER BY`, donc la MLE sommait dans un ordre dépendant du build → notes différentes à la 3ᵉ décimale d'un run à l'autre (contredisant la reproductibilité revendiquée dans les ADRs). Ordonner l'entrée du fit rend deux runs byte-identiques.

### État
- `main` au commit backfill historique ; CI verte (checks + frontend). dbt build : **85 nœuds** PASS (était 67). Python : **67 tests** (48 unit + 19 contract), ruff + pyright propres. Déployé : https://dashboard-mathis7.vercel.app (section historique + `/dbt-docs` vérifiés 200).

### Ouverts / suite
- **Action owner pour activer l'auto-deploy :** ajouter le secret `VERCEL_TOKEN` et les vars `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` (deploy.yml skip proprement en attendant). D'ici là, le déploiement prod reste le manuel `cd dashboard && npx vercel --prod --yes`.
- Crédits photos du footer toujours en attente avant partage large.
- Le compteur « runs » n'apparaît sur le site qu'après le premier run cron qui peuple `data/ops/runs.jsonl`.

---

## Session 2026-08-05 — moteur d'analyse, essai long-format, données réelles SofaScore ✅

Session autonome (droits donnés par Mathis en fin de soirée : « termine, je dors, je regarde demain »). Prolonge directement la Phase 3 : le dashboard passe d'un rapport visuel à une **vraie démonstration data science**.

### Fait
- **Moteur d'analyse (`analytics/`)** : modèle de force Poisson (attaque/défense/avantage terrain) ajusté par maximum de vraisemblance pénalisé (scipy `L-BFGS-B`, ridge=0.05) sur les 104 résultats. Dérive buts/points **modélisés** (jamais appelés xG — honnêteté sur l'absence de données de tir), sur/sous-performance, upsets, et une **simulation Monte-Carlo** (10 000 tirages) du tableau à élimination directe reconstruit à partir des seuls résultats (pas de lien parent/enfant dans la donnée source). `python -m analytics` lit `warehouse.duckdb`, écrit tous les JSON front. Câblé dans le workflow quotidien après l'export (gate d'échec inclus).
- **Essai long-format « L'Espagne méritait-elle son titre ? »** : section flagship `#analyse`, prose développée (paragraphes rédigés, pas des puces), 7 figures numérotées (scatter attaque×défense, dumbbell points réels/attendus, parcours de l'Espagne, probabilité de titre, heatmap de progression, tableau de stats réelles, carte de tirs), verdict, note méthodo. Section « Le modèle, à nu » dans Méthode : équation Poisson, `fit()` en CodeBlock terminal, **et maintenant aussi `play()`** (la récursion Monte-Carlo) avec l'explication de la reconstruction du tableau — ajouté cette session pour que l'algo de simulation soit expliqué avec le même niveau de détail que l'ajustement du modèle.
- **Deuxième source de données réelles (SofaScore, via SportApi7/RapidAPI, quota gratuit 50 req/mois)** : `ingestion/sofascore.py` (one-off, tournoi terminé → run une fois, ~13 requêtes consommées, 30 restantes) récupère les 8 matchs de l'Espagne (xG réel, possession, tirs) + les 5 shotmaps des matchs à élimination directe. `analytics/real_stats.py` réconcilie par chronologie (les deux sources n'ont pas d'ID commun) et croise le xG réel avec le xG modélisé — **validation indépendante du modèle**. Nouveau composant `Shotmap.astro` (carte SVG des tirs, taille ∝ xG, but en or). Clé RapidAPI ajoutée à `.env` local avec autorisation explicite de Mathis (« je t'autorise à la mettre dans le .env »), jamais commitée.
- **Bug de rendu trouvé et corrigé (les deux CodeBlocks)** : Astro/JSX supprime l'indentation en début de ligne quand elle touche directement une frontière de tag (`</i>` suivi d'une nouvelle ligne commençant du texte, ou l'inverse) — ça cassait l'affichage du code Python (indentation perdue, lignes fusionnées). Corrigé en encodant l'indentation sensible avec des entités `&#32;` plutôt que des espaces littéraux ; ça corrige aussi un bug **déjà en production** dans le bloc `fit()` (jamais repéré visuellement avant, la vérification précédente ne portait que sur le débordement horizontal, pas la justesse du code affiché).
- **Qualité** : `ruff check` propre, 24 tests pytest verts, build Astro propre, `shoot.mjs` confirme zéro débordement horizontal desktop/mobile. Carte Graphify régénérée (passe AST uniquement, cohérent avec la dette déjà connue — 306 nœuds AST, 275 après filtrage, 393 arêtes, 29 communautés ; le health-check signale 51 arêtes aux extrémités pendantes, stable par rapport aux ~56 déjà documentées avant Phase 3 — dette pré-existante liée au mélange code Python/Astro + JSON de données, pas une régression de cette session).

### Écarts / points ouverts
- Le shotmap et les stats réelles ne couvrent que l'Espagne (contrainte de quota, documentée honnêtement dans la section méthode).
- Graphify : la passe sémantique complète (docs/markdown) reste différée, comme documenté depuis la Phase 0 — AST-only reste la norme établie du projet.
- `assets/` (photos sources brutes, déjà traitées dans `dashboard/public/photos`) ajouté au `.gitignore` — n'était pas versionné avant non plus, juste rendu silencieux dans `git status`.

## Session Phase 3 — dashboard public (Astro) ✅ (mergé PR #26)

### Décisions d'architecture
- **Evidence abandonné** (acté avec le cerveau) au profit d'un front **custom Astro** (0 JS par défaut) pour une identité distinctive. Archi 100% statique conservée : marts DuckDB → export JSON commité → build Astro → Vercel (intégration Git).
- **Pont données** : `dashboard/scripts/export_marts.py` (DuckDB → JSON). Le front ne dépend JAMAIS de Python/dbt pour builder — il lit les JSON commités (`dashboard/src/data/`).

### Fait
- **Direction artistique** (skill `frontend-design` officiel installé, méthode 2 passes) : hybride éditorial + terminal. Papier `#f0ede4` + encre `#17150f`, **un seul accent** vert « pelouse sous projecteurs » `#0c5a3a` (terracotta évité), **Fraunces + IBM Plex Mono** self-hostées. Signature = le **bandeau live-feed** (fraîcheur réelle du pipeline en écran de scoreboard). Photos en **duotone vert/papier** (CSS blend).
- **4 pages** : Accueil (chiffres géants + count-up, derniers/prochains matchs, bande duotone) · Groupes (12 tables recalculées, qualif encodée dans l'accent : plein=top2, hachuré=meilleur 3e ; note **réconcilié 48/48**) · Phase finale (bracket, entonnoir horizontal desktop / empilé mobile) · Méthode (pipeline en séquence numérotée, test de réconciliation en 3 phrases, stack + repo).
- **Intégration** : le workflow quotidien enchaîne `dbt build` → export JSON → publie **raw + JSON dans une seule PR auto** (label `data`) ; le raw reste publié même si dbt/export échoue (gate final re-échoue le job → issue). CI + job `frontend` (build Astro sans réseau). `vercel.json` + badges.
- **Qualité** : contraste **WCAG AA** partout (ink-faint assombri en `#645e4c`), titres sémantiques, tables `<th scope>`, fontes subset self-host, `prefers-reduced-motion` respecté, contenu **visible sans JS** (`html.js` gate), **zéro débordement horizontal à 390px** (helper puppeteer `scripts/shoot.mjs` : scrollW==clientW sur les 4 pages). Vérifié visuellement desktop + mobile.
- **Maintenance (tâche zéro)** : carte Graphify reconstruite proprement (AST-only, plus de 56 arêtes orphelines). Micro-chantiers : **aucun test dbt déprécié** (déjà en `data_tests:` depuis Phase 2, WARN=0) ; README commandes de repro + note filtre `is:pr -label:data` ; label `data` sur les PR du bot.

### À faire par Mathis (dernier maillon)
- **Connecter le repo à Vercel** (compte perso) : New Project → import `wc26-data-pipeline` → **Root Directory = `dashboard`** (framework Astro auto-détecté) → Deploy. Chaque merge sur `main` (code OU données du matin) redéploiera. Aucune CLI ni token en CI.
- **Crédits photos** : footer en placeholder « à compléter » — renseigner auteur+source avant diffusion large (une des photos est une archive 2002, légende neutralisée en « image d'illustration »).

### Écarts / points ouverts
- Aperçu Artifact non produit : Mathis a vu les 4 pages en captures inline (desktop+mobile) ; le vrai aperçu interactif = le preview deploy Vercel.
- Bracket sans connecteurs (la donnée ne garantit pas les liens tour-à-tour) — colonnes par tour, honnête.
- Graphify : passe sémantique complète encore à refaire (coupée par la limite de session) — AST-only en place, cohérent.

## Session 2026-07-12 — Phase 2 : modélisation dbt ✅

### Fait
- **Workflow git durci** : branche `feat/dbt-phase-2`, ruleset `protect-main` (PR obligatoire, force-push/suppression interdits, admin en bypass), alerte `if: failure()` qui ouvre une issue horodatée (testée en réel : issue #1 ouverte puis fermée), actions bumpées (`checkout@v7`, `setup-uv@v8.3.2`).
- **Init dbt** : dbt-core 1.11 + dbt-duckdb 1.10 (groupe uv dédié), warehouse DuckDB jetable gitignoré, sources en `external_location` avec `hive_partitioning` + `union_by_name` (obligatoire). Validé : 208 lignes matches / 96 standings sur 2 partitions.
- **Staging** : `stg_matches` + `stg_standings` (views) — structs dépliés, timestamps castés, `group_code` canonique (piège `GROUP_A` vs `Group A` neutralisé, jointure vérifiée). 17 tests verts, volumétrie = source.
- **Marts** : `int_matches_latest` (dernier snapshot centralisé, 104), `dim_teams` (48 exactement), `fct_matches` (104 exactement, relationships), `fct_group_standings` — critères FIFA 1-3 + **couche h2h** (4-6) + fair-play documenté indisponible (7) + fallback `team_name` déterministe (8). **2 unit tests dbt** (égalité parfaite tranchée par h2h ; égalité circulaire → alphabétique).
- **Test de réconciliation** `assert_computed_standings_match_official` : full outer anti-join calculé vs officiel — **48/48**, détection de divergence vérifiée par sabotage (+1 point → ligne fautive renvoyée).
- **Intégration** : `dbt build` dans le workflow quotidien (le raw est publié AVANT dbt — un échec de modélisation ne coûte jamais un jour de capture), CI de PR (ruff + pytest + dbt build), badges README, `dbt docs generate` OK en local.
- `dbt build` complet : **46/46 nœuds verts**.

### Écart au brief (à arbitrer si besoin)
- **Bypass bot impossible** : GitHub refuse l'app `github-actions` comme bypass actor d'un ruleset sur un repo personnel (API, confirmé ×3) et l'ajout UI n'a pas abouti. Solution en place : **le bot publie le raw via une mini-PR auto-fusionnée** (squash) — conforme à la règle PR, validé en réel (PR #3). Conséquence : une PR de données par jour dans l'historique.

### Questions ouvertes
1. Le sous-classement h2h est non récursif (un seul niveau, conforme au brief) ; la vraie règle FIFA réapplique récursivement les critères sur le sous-ensemble restant. À traiter au backfill historique si des cas réels l'exigent ?
2. `row_count_equals` fige 104/48 pour l'édition 2026 — à paramétrer par édition lors du backfill.
3. Publication des dbt docs (GitHub Pages vs Vercel) — phase ultérieure.

## Addendum 2026-07-11 — pipeline EN PRODUCTION ✅

- Clé API football-data.org reçue → `.env` local (gitignoré) + secret GitHub `FOOTBALL_DATA_API_KEY`.
- Client amélioré suivant la recommandation du fournisseur : throttling automatique via les headers `X-Requests-Available-Minute` / `X-RequestCounter-Reset` (19 tests verts).
- **Smoke test réel réussi** : l'id `WC` couvre bien la WC 2026 sur le free tier → 104 matchs (98 FINISHED, 6 TIMED), 48 lignes de classement. Question ouverte n°1 d'hier : résolue.
- Repo GitHub public créé : `mathis-tl/wc26-data-pipeline`, tout poussé.
- **Run CI de bout en bout validé** (`workflow_dispatch`) : ingestion → 104+48 lignes loggées → commit `data: raw ingestion 2026-07-11` poussé par le bot. Le cron quotidien 06:00 UTC est armé.
- Point mineur relevé en CI : annotation de dépréciation Node 20 sur `actions/checkout@v4` / `setup-uv@v6` — bump à prévoir, non bloquant.
- Reste côté Mathis : cliquer le lien de vérification e-mail de football-data.org (sinon suppression du compte pour inactivité).

---

# Session 2026-07-10 (Phase 0 + Phase 1)

## Fait

**Setup**
- Skills installés dans `~/.claude/skills/` : les 10 skills officiels dbt-labs + `dbt-develop` et `dbt-troubleshoot` (Altimate).
- Outillage machine : `uv` 0.11 et `gh` 2.96 installés via Homebrew.
- Carte Graphify générée puis régénérée en fin de session (129 nœuds, 217 arêtes, 9 communautés — `graphify-out/`, non versionné).

**Phase 0 — scaffolding** (4 commits)
- `git init` (branche `main`), structure `ingestion/ tests/ dbt/ dashboard/ .github/workflows/ data/raw/`.
- `pyproject.toml` géré par uv, Python 3.12 épinglé, lockfile commité. Deps : httpx, pyarrow, python-dotenv, tenacity ; dev : pytest, respx, ruff.
- `.env.example` (2 clés API), `.gitignore`, `README.md` squelette.

**Phase 1a — client API** (2 commits)
- `ingestion/client.py` : `FootballDataClient` (football-data.org v4), rate-limit 6 s intégré (10 req/min garanti), retries tenacity avec backoff exponentiel + respect du `Retry-After` sur 429, fail-fast sur les autres 4xx, log du nombre de lignes à chaque fetch.
- 10 tests pytest/respx, tous verts.

**Phase 1b — écriture Parquet** (2 commits)
- `ingestion/storage.py` : partitions Hive `data/raw/football_data/{dataset}/extraction_date=YYYY-MM-DD/`, écriture atomique (tmp + replace), idempotence par remplacement (2 runs même jour = 1 fichier), structs imbriqués préservés (fidélité raw), colonnes `extracted_at`/`source`, contrôle lignes reçues = lignes écrites (exception sinon), cas 0 ligne loggé.
- `ingestion/__main__.py` : `uv run python -m ingestion`.
- 7 tests supplémentaires (17 au total, tous verts, ruff propre).

**Phase 1c — workflow CI** (1 commit)
- `.github/workflows/ingest.yml` : cron 06:00 UTC + `workflow_dispatch`, setup-uv avec cache, `uv sync --frozen`, ingestion, commit/push de `data/raw/` par le bot si changement.

## Non fait

- **Push GitHub** : `gh` non authentifié (`gh auth login` est interactif). Repo `wc26-data-pipeline` (public) à créer + push + `gh secret set FOOTBALL_DATA_API_KEY` dès que l'auth est faite.
- **Smoke test réel de l'ingestion** : pas encore de clé API football-data.org (pas de `.env`). Donc l'id de compétition `WC` pour la WC 2026 sur le free tier n'est **pas encore vérifié en réel**.
- Backfill openfootball (prévu Phase 1, non urgent — données stables).
- Client API-Football (stats joueurs) — pas dans le périmètre de cette session.

## Décisions (validées par Mathis)

1. **`data/raw/` versionné dans git** (pas d'artefacts CI) : volume négligeable (< 5 Mo pour le tournoi), l'historique de commits = preuve horodatée que le pipeline a tourné pendant le tournoi, artefacts GitHub expirent à 90 j.
2. **Nom du repo GitHub : `wc26-data-pipeline`** (public).
3. Fixtures et résultats = **un seul endpoint** `/competitions/WC/matches` (distinction par `status`) → 2 appels API par run (matches + standings), pas 3.
4. Raw en Parquet **structs imbriqués** (tous les champs API préservés) plutôt que JSON texte en colonne.
5. Idempotence par **remplacement du fichier du jour** (nom déterministe par date d'extraction).
6. Cron à **06:00 UTC** (fin des matchs en Amérique du Nord ~04-05 UTC).

## Écarts / signalements

- `PROJECT_PLAN.md` n'existe pas ; le plan est `PLAN.md` — aligner le prompt de session.
- Le skill Altimate `creating-dbt-models` n'existe plus ; remplacé par `dbt-develop` (installé).
- Health check Graphify : 26 arêtes à extrémité manquante (mismatch d'IDs sémantique/AST autour de `__main__`) — carte utilisable, à nettoyer lors d'une prochaine régénération complète.

## Questions ouvertes (pour le Claude cerveau)

1. Le free tier football-data.org expose-t-il bien la WC 2026 sous l'id `WC` ? À vérifier au premier run réel (smoke test dès que la clé existe).
2. Faut-il ajouter une notification d'échec (issue auto ou mail) au workflow dès la V1, ou attendre la Phase 4 comme prévu au plan ?
3. Pour la Phase 2 : le raw en structs imbriqués implique `read_parquet(..., hive_partitioning=true)` + dépliage des structs dans les modèles staging dbt — OK pour partir là-dessus ?
4. La branche protégée / PR obligatoire n'est pas configurée — le workflow pushe sur `main` directement. Acceptable en V1 ?
