# SESSION_NOTES

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
