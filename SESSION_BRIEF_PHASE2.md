# Session : WC26 Pipeline — Phase 2 : modélisation dbt

## Rôles
Tu es l'exécutant technique. L'architecture est décidée en amont (Mathis +
Claude "cerveau") et documentée dans `PLAN.md`. Ce brief contient des décisions
DÉJÀ VALIDÉES sur données réelles — ne les remets pas en cause. Si tu détectes
un problème, signale-le et attends l'arbitrage de Mathis.

## Rituel de session (inchangé)
Cartographie Graphify → diagnostic → proposition → validation par Mathis →
implémentation. Jamais de code avant validation. Utilise les skills dbt-labs
et Altimate (`dbt-develop`, `dbt-troubleshoot`) installés en Phase 0.
Fin de session : régénère la carte Graphify + addendum SESSION_NOTES.md.

## Changement de workflow git — À FAIRE EN PREMIER
À partir de cette session : plus de push direct sur `main` pour le code.
1. Crée une branche `feat/dbt-phase-2`, travaille dessus, PR à la fin.
2. Configure un ruleset GitHub protégeant `main` (PR obligatoire) avec le
   bot `github-actions` en bypass actor — SINON les commits quotidiens du
   raw casseront. Vérifie après coup que le cron d'ingestion passe encore.
3. Ajoute au workflow d'ingestion un step `if: failure()` qui ouvre une
   issue GitHub (titre horodaté, lien vers le run). Décision actée : alerte
   minimale dès maintenant, la finale est le 19/07.

## Contexte données (vérifié sur le raw réel du 12/07)
- `data/raw/football_data/matches/extraction_date=*/matches.parquet` :
  104 matchs, structs imbriqués (homeTeam, awayTeam, score avec fullTime/
  halfTime/extraTime/penalties, referees en liste). `utcDate` et
  `lastUpdated` sont des VARCHAR → à caster en staging.
- `data/raw/football_data/standings/...` : 48 lignes, positions officielles.
- ⚠️ PIÈGE CONFIRMÉ : le format du groupe diffère entre endpoints —
  matches = `GROUP_A`, standings = `Group A`. Normaliser en staging vers
  un `group_code` canonique (la lettre seule : 'A'…'L').
- Stages présents : GROUP_STAGE, LAST_32, LAST_16, QUARTER_FINALS,
  SEMI_FINALS, THIRD_PLACE, FINAL.

## Objectifs de la session (dans l'ordre, validation entre chaque)

### 1. Init dbt
- `dbt-core` + `dbt-duckdb` en dépendances (groupe dédié dans pyproject).
- Projet dbt dans `dbt/` (il existe déjà vide), profil DuckDB local,
  fichier de base `data/warehouse.duckdb` (gitignoré).
- Sources déclarées en YAML pointant vers le raw via `external_location` :
  `read_parquet('data/raw/football_data/<dataset>/*/*.parquet',
  hive_partitioning=true, union_by_name=true)` — le `union_by_name` est
  OBLIGATOIRE (protection schema drift entre partitions).

### 2. Staging (materialization: view)
- `stg_matches` : dépliage des structs (match_id, kickoff_at TIMESTAMP,
  stage, group_code normalisé, status, home/away team_id + name + tla,
  scores fullTime/halfTime/extraTime/penalties à plat, winner), 1 ligne
  par match ET par extraction_date (le staging garde l'historique des
  snapshots ; le filtrage "dernier snapshot" se fait dans les marts via
  `QUALIFY row_number() OVER (PARTITION BY match_id ORDER BY
  extraction_date DESC) = 1` ou un modèle intermédiaire dédié).
- `stg_standings` : idem (team_id, group_code normalisé, position, points,
  played/won/draw/lost, goals_for/against/diff, extraction_date).
- Tests staging : `not_null` + `unique` sur les clés composites
  (match_id, extraction_date) / (team_id, extraction_date) ;
  `not_null` sur les casts TIMESTAMP (attrape un changement de format) ;
  `accepted_values` sur status et sur group_code (A-L).

### 3. Cœur des marts (materialization: table)
- `dim_teams` : 1 ligne/équipe (dernier snapshot), depuis stg_standings +
  équipes vues dans stg_matches. Test : exactement 48 lignes.
- `fct_matches` : 1 ligne/match, dernier snapshot. Test volumétrie :
  exactement 104 lignes (compétition complète), relationships vers dim_teams.
- `fct_group_standings` : LE morceau. Calculé UNIQUEMENT depuis fct_matches
  (pas depuis standings !). Règles FIFA dans l'ordre :
  1-3 : points DESC, goal_diff DESC, goals_for DESC ;
  4-6 : en cas d'égalité parfaite 1-3, sous-classement recalculé sur les
  seules confrontations directes entre équipes à égalité (points h2h,
  diff h2h, buts h2h) ;
  7 : fair-play — NON DISPONIBLE dans le free tier → documenter la
  limitation dans le YAML du modèle (pas de silence là-dessus) ;
  8 : tirage au sort → fallback déterministe team_name ASC, documenté.
  Le prototype SQL validé (critères 1-3 + normalisation) est en annexe —
  pars de là, ajoute la couche h2h.

### 4. Test de réconciliation (pièce maîtresse)
Test dbt custom (fichier dans `tests/`) : anti-jointure entre
`fct_group_standings` et le classement officiel (stg_standings, dernier
snapshot). Toute ligne où (points, goal_diff, goals_for, position)
divergent = échec. Vérifié sur le raw du 12/07 : doit passer 48/48.
C'est le test d'intégrité de bout en bout du pipeline — soigne son nom
et sa description YAML, il sera montré en entretien.

### 5. Intégration
- `dbt build` complet vert en local.
- Étend le workflow d'ingestion : après l'ingestion, exécuter `dbt build`
  (le warehouse DuckDB est jetable, reconstruit à chaque run — ne PAS le
  committer). Si dbt échoue, le workflow échoue → issue auto.
- CI de PR : ruff + `dbt build` sur les données du repo. Badge README.
- `dbt docs generate` fonctionne en local (publication = phase ultérieure).

## Règles non négociables (rappel)
- Aucune jointure/dédup/filtre ne droppe de lignes silencieusement :
  chaque modèle intermédiaire a ses tests de volumétrie.
- Tests d'abord sur les clés, ensuite sur la sémantique.
- Commits atomiques conventionnels, en anglais, sur la branche de feature.
- Si `dbt build` échoue 3 fois de suite sur le même problème : stop,
  résumé du blocage, on remonte au cerveau.

## Annexe — prototype validé (référence d'implémentation)
```sql
-- Validé le 12/07 sur raw réel : réconciliation 48/48 stats et positions
-- (critères 1-3 seuls ; aucune égalité parfaite dans cette édition,
--  le h2h reste à implémenter et sera testé sur le backfill historique)
WITH stg_matches AS (
  SELECT id AS match_id, stage, status,
    replace("group", 'GROUP_', '') AS group_code,
    homeTeam.id AS home_team_id, homeTeam.name AS home_team_name,
    awayTeam.id AS away_team_id, awayTeam.name AS away_team_name,
    score.fullTime.home AS home_goals, score.fullTime.away AS away_goals
  FROM read_parquet('data/raw/football_data/matches/*/*.parquet',
                    hive_partitioning=true, union_by_name=true)
),
group_matches AS (
  SELECT * FROM stg_matches WHERE stage='GROUP_STAGE' AND status='FINISHED'
),
team_match AS (
  SELECT group_code, home_team_id AS team_id, home_team_name AS team_name,
         home_goals AS gf, away_goals AS ga FROM group_matches
  UNION ALL
  SELECT group_code, away_team_id, away_team_name, away_goals, home_goals
  FROM group_matches
),
computed AS (
  SELECT group_code, team_id, team_name, COUNT(*) AS played,
    SUM(CASE WHEN gf>ga THEN 3 WHEN gf=ga THEN 1 ELSE 0 END) AS points,
    SUM(gf) AS goals_for, SUM(gf)-SUM(ga) AS goal_diff
  FROM team_match GROUP BY 1,2,3
)
SELECT *, ROW_NUMBER() OVER (
  PARTITION BY group_code
  ORDER BY points DESC, goal_diff DESC, goals_for DESC, team_name
) AS position
FROM computed
```
NB staging réel : garder la granularité (match_id, extraction_date) et
filtrer le dernier snapshot dans les marts — le prototype lit tout le raw
et fonctionnera tant qu'un match n'apparaît que dans des snapshots
cohérents ; le modèle final doit être explicite sur ce point.

Commence par lire PLAN.md et ce brief en entier, génère la carte Graphify,
puis propose ton plan d'attaque pour l'étape 1 (workflow git + init dbt).
N'écris AUCUN code avant validation.
