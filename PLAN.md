# World Cup 2026 Data Pipeline — Plan de projet

> Projet portfolio data engineering. Stack 100% gratuit.
> Objectif : démontrer les compétences attendues d'un data engineer junior
> (orchestration, modélisation SQL, tests de données, CI/CD, déploiement).

---

## 1. Glossaire — les termes techniques du projet

### Concepts généraux

**Pipeline (de données)** — Chaîne automatisée d'étapes qui déplace et transforme
de la donnée d'une source (ici : des APIs football) vers une destination
exploitable (ici : un dashboard). Chaque étape prend en entrée la sortie de la
précédente.

**Batch vs Streaming** — *Batch* : le pipeline tourne à intervalle régulier
(ex. 1x/jour) et traite un lot de données d'un coup. *Streaming* : les données
sont traitées en continu, événement par événement, en quasi temps réel.
Notre projet est **batch** : pas besoin de temps réel pour un dashboard
analytique.

**ETL vs ELT** — Deux ordres d'opérations. *ETL* (Extract, Transform, Load) :
on transforme la donnée AVANT de la charger dans la base. *ELT* (Extract, Load,
Transform) : on charge d'abord la donnée brute, puis on transforme DANS la base
avec du SQL. L'approche moderne (et la nôtre) est **ELT** : la donnée brute est
conservée intacte, les transformations sont rejouables à volonté.

**Ingestion** — La partie "E + L" de l'ELT : aller chercher la donnée à la
source (appels API) et la déposer telle quelle dans notre stockage.

**Backfill** — Charger rétroactivement des données historiques (ex. les Coupes
du Monde 1930-2022) alors que le pipeline normal ne traite que les données
récentes. C'est souvent un mode d'exécution spécial du même pipeline.

**Idempotence** — Propriété clé d'un bon pipeline : le rejouer plusieurs fois
sur les mêmes données produit exactement le même résultat (pas de doublons,
pas de corruption). Concrètement : si le run de 14h échoue à moitié et qu'on
relance à 15h, tout est propre. S'obtient avec des upserts, des clés uniques,
et des écritures par remplacement plutôt que par ajout aveugle.

### Architecture en couches (architecture "médaillon")

Organisation du stockage en 3 couches de qualité croissante. Aussi appelée
bronze/silver/gold. Chez nous :

**Raw (bronze)** — La donnée EXACTEMENT comme l'API l'a renvoyée, sans aucune
modification. Format : fichiers Parquet horodatés. Règle d'or : on n'y touche
JAMAIS. C'est notre filet de sécurité : si une transformation a un bug, on
peut tout reconstruire depuis le raw sans re-appeler l'API.

**Staging (silver)** — La donnée nettoyée et normalisée : types corrects
(dates en DATE, scores en INT), noms de colonnes homogènes (snake_case),
doublons éliminés, IDs réconciliés entre les sources. Une table staging =
une source raw, nettoyée. Pas encore de logique métier.

**Marts (gold)** — Les tables FINALES, modelées pour répondre aux questions
métier, prêtes à brancher sur le dashboard. "Mart" vient de "data mart" =
comptoir de données. C'est ici qu'on croise, agrège, calcule. Exemples chez
nous : classement des groupes, stats par équipe, top buteurs.

### Modélisation dimensionnelle (le format des marts)

**Table de faits (fact table, préfixe `fct_`)** — Table qui enregistre des
ÉVÉNEMENTS mesurables : un match, un but. Beaucoup de lignes, des chiffres,
des clés étrangères vers les dimensions. Ex : `fct_matches` (1 ligne = 1 match).

**Table de dimension (dim table, préfixe `dim_`)** — Table qui décrit des
ENTITÉS : une équipe, un joueur, un stade. Peu de lignes, beaucoup d'attributs
descriptifs. Ex : `dim_teams` (1 ligne = 1 équipe, avec confédération, rang
FIFA, etc.).

**Schéma en étoile (star schema)** — L'organisation classique : les tables de
faits au centre, reliées aux dimensions autour. C'est LE vocabulaire attendu
en entretien data engineering.

### Les outils

**dbt (data build tool)** — L'outil standard de la couche Transform. On écrit
des modèles = des fichiers SQL (1 fichier = 1 table ou vue), dbt gère l'ordre
d'exécution, les dépendances, les tests et la documentation. Vocabulaire dbt :
- **Model** : un fichier `.sql` qui définit une table/vue via un SELECT.
- **Source** : déclaration YAML des tables brutes en entrée (notre raw).
- **ref()** : fonction pour référencer un autre modèle ; c'est comme ça que
  dbt construit le graphe de dépendances.
- **Materialization** : COMMENT le modèle est créé physiquement — `view`
  (vue SQL, recalculée à chaque lecture), `table` (table physique reconstruite
  à chaque run), `incremental` (on n'ajoute que les nouvelles lignes).
- **Test** : assertion sur la donnée (`not_null`, `unique`, `relationships`,
  ou SQL custom). Un test qui échoue = le build échoue. C'est la réponse
  directe à l'anti-pattern des pertes silencieuses de données.
- **dbt docs** : documentation auto-générée avec le graphe de lignage.

**Lineage (lignage)** — Le graphe qui montre d'où vient chaque table et qui
dépend d'elle. Raw → staging → marts, visualisable dans dbt docs.

**DuckDB** — Base de données analytique (OLAP) *in-process* : pas de serveur,
c'est une librairie Python + un fichier local (comme SQLite, mais orienté
analytique). Ultra rapide sur des agrégations, lit le Parquet nativement.
- **OLAP vs OLTP** : *OLTP* (transactionnel, ex. PostgreSQL) = optimisé pour
  beaucoup de petites lectures/écritures ligne par ligne (une app web).
  *OLAP* (analytique) = optimisé pour scanner des millions de lignes et
  agréger (un dashboard). Les bases OLAP stockent en colonnes, pas en lignes.

**Parquet** — Format de fichier colonne, compressé, typé. Le standard de facto
pour stocker de la donnée analytique. Beaucoup plus efficace que CSV/JSON :
plus petit, plus rapide à lire, et le schéma (types) est embarqué.

**Orchestration** — Le "chef d'orchestre" qui déclenche les étapes du pipeline
dans le bon ordre, au bon moment, gère les échecs (retries) et garde
l'historique des exécutions. Tu connais Prefect ; ici on démarre avec GitHub
Actions (suffisant en V1), Dagster en V2 optionnelle.

**DAG (Directed Acyclic Graph)** — Graphe orienté sans cycle : la représentation
formelle d'un pipeline (étape A avant B, B avant C, pas de boucle). Tous les
orchestrateurs raisonnent en DAG. Les modèles dbt forment aussi un DAG.

**Cron** — La syntaxe standard Unix pour planifier une exécution récurrente.
Ex : `0 6 * * *` = tous les jours à 6h00 UTC.

**CI/CD** — *Continuous Integration* : à chaque push, des vérifications
automatiques tournent (lint, tests, `dbt build` sur un échantillon).
*Continuous Deployment* : si tout est vert, déploiement automatique.
Chez nous, les deux vivent dans GitHub Actions.

**GitHub Actions** — Le service de CI/CD de GitHub. Gratuit pour les repos
publics. On y définit des *workflows* (fichiers YAML dans
`.github/workflows/`) déclenchés par un push, un cron, ou manuellement.
Il jouera 2 rôles distincts chez nous : CI (qualité du code) ET scheduler
du pipeline (rôle d'orchestrateur minimal).

**Evidence** — Outil de "BI-as-code" : on écrit le dashboard en Markdown + SQL,
Evidence le compile en site web statique. Versionnable dans Git, gratuit,
se marie nativement avec DuckDB.

**Site statique** — Site composé uniquement de fichiers HTML/CSS/JS générés à
l'avance ("au build"). Pas de serveur applicatif, pas de base de données
interrogée en direct : les données du dashboard sont figées au moment du
build. Conséquence : rafraîchir les données = relancer le build + redéployer.
C'est notre modèle : chaque run du pipeline régénère le site.

**Vercel** — Plateforme d'hébergement de sites statiques/front. Plan Hobby
gratuit (usage non commercial). Un **Deploy Hook** est une URL secrète
fournie par Vercel : l'appeler (simple requête HTTP) déclenche un
redéploiement — c'est comme ça que le pipeline dira "nouvelles données,
republie le site".

**Monitoring / Observabilité** — Savoir que le pipeline a tourné, réussi ou
échoué, en combien de temps, sur combien de lignes. V1 : notifications
d'échec GitHub Actions + compteurs de lignes loggés + tests dbt.

---

## 2. Le plan complet

### 2.1 Objectif et livrables

| Livrable | Public visé | Rôle |
|---|---|---|
| Repo GitHub propre (README, docs, CI verte) | Recruteurs tech | La preuve technique |
| Dashboard public sur Vercel | Tout le monde | La preuve visible, lien sur le CV |
| dbt docs publiées (lignage + tests) | Recruteurs data | La preuve de rigueur |
| Article de blog "architecture & choix" | Recruteurs + LinkedIn | La preuve de recul |

### 2.2 Architecture cible

```
┌─────────────────────── SOURCES ───────────────────────┐
│ football-data.org (free, WC incluse, 10 req/min)      │
│ API-Football (free, 100 req/jour — stats joueurs)     │
│ openfootball/worldcup.json (open data, historique)    │
└───────────────────────┬────────────────────────────────┘
                        │ Python (httpx, retry, rate-limit)
                        ▼
        RAW — Parquet horodatés (data/raw/)
                        │ dbt-duckdb
                        ▼
        STAGING — nettoyage, typage, dédup, IDs réconciliés
                        │ dbt-duckdb (+ tests à chaque couche)
                        ▼
        MARTS — schéma en étoile (fct_ / dim_)
                        │ Evidence build
                        ▼
        Site statique ──► Vercel (deploy hook)

Orchestration : GitHub Actions (cron) │ CI : lint + dbt build + tests
Coût total : 0 €/mois
```

### 2.3 Modèle de données cible (les marts)

Dimensions :
- `dim_teams` — équipes (confédération, groupe 2026, palmarès historique)
- `dim_players` — joueurs (poste, club, sélection)
- `dim_matches` — métadonnées match (stade, ville, phase, date)
- `dim_tournaments` — les 23 éditions (année, hôte, format)

Faits :
- `fct_matches` — 1 ligne / match : scores, vainqueur, phase (2026 + historique)
- `fct_goals` — 1 ligne / but : buteur, minute, type (si dispo dans les sources)
- `fct_group_standings` — classements de groupes calculés avec les règles FIFA
  de départage (le morceau SQL le plus intéressant du projet)

Marts d'analyse (pour le dashboard) :
- `mart_team_performance` — stats agrégées par équipe et par édition
- `mart_top_scorers` — meilleurs buteurs 2026 + all-time
- `mart_tournament_comparison` — 2026 (48 équipes) vs éditions précédentes
- `mart_upsets` — surprises : victoires contre le classement FIFA

### 2.4 Périmètre

**Dans le scope (V1)**
- Ingestion 2026 (fixtures, résultats, classements) + backfill 1930-2022
- Modélisation dbt 3 couches, tests sur chaque couche, docs publiées
- Dashboard Evidence déployé sur Vercel
- Pipeline schedulé + CI/CD + notifications d'échec
- README soigné + article de blog

**Hors scope V1 (extensions V2 possibles)**
- Streaming / temps réel
- Modèle de prédiction ML
- Migration de l'orchestration vers Dagster
- Cotes bookmakers

### 2.5 Contrainte calendrier — IMPORTANT

La finale est le **19 juillet 2026**. Il reste ~9 jours de matchs live
(phases finales). Conséquence sur les priorités :

> **Priorité absolue de la semaine 1 : un script d'ingestion minimal qui
> tourne chaque jour et archive le raw.** Même moche, même lancé à la main.
> Chaque jour de match non capturé en raw pendant le tournoi est une donnée
> qu'il faudra récupérer autrement après (possible — football-data.org garde
> la saison en cours, openfootball reste dispo — mais on perd le storytelling
> "mon pipeline a tourné PENDANT le tournoi").

Le reste (dbt, dashboard, CI) peut se construire tranquillement en juillet-août
sur le raw accumulé. Le projet reste 100% pertinent après la finale : il
devient un projet analytique sur données complètes.

### 2.6 Phases

**Phase 0 — Setup (1 soirée, à faire AVANT le 12/07)**
Repo GitHub public, uv/venv, clés API (football-data.org + API-Football),
structure de dossiers, `.env` + secrets GitHub Actions.

**Phase 1 — Ingestion raw (semaine 1 : 10-16 juillet) ⚡ urgent**
Script Python : fetch fixtures/résultats/standings 2026 → Parquet horodatés.
Rate-limiting (10 req/min), retries, logs avec compteurs de lignes.
Cron GitHub Actions quotidien DÈS QUE le script marche.
Backfill historique openfootball (pas urgent, données stables).

**Phase 2 — Modélisation dbt (semaines 2-3 : 17-30 juillet)**
Init dbt-duckdb, sources YAML, staging (typage, dédup, réconciliation d'IDs
entre les 3 sources), puis marts (star schema ci-dessus).
Tests : `unique` + `not_null` sur toutes les clés, `relationships` entre
faits et dimensions, tests custom (ex : nb de matchs par édition = attendu —
le garde-fou anti "pertes silencieuses").
`dbt docs generate` publié (GitHub Pages ou Vercel).

**Phase 3 — Dashboard Evidence (semaines 4-5 : 31 juillet - 13 août)**
Pages : Accueil tournoi 2026 · Classements & bracket · Top buteurs ·
Comparaison historique · Page "upsets".
Build local branché sur le DuckDB des marts, puis déploiement Vercel.

**Phase 4 — Industrialisation (semaine 6 : 14-20 août)**
Workflow complet bout-en-bout : ingestion → dbt build → Evidence build →
deploy hook Vercel. CI sur PR (lint ruff, dbt build + tests sur échantillon).
Notifications d'échec. Badge CI dans le README.

**Phase 5 — Vitrine (semaines 7-8 : 21 août - 3 septembre)**
README avec schéma d'archi, GIF du dashboard, section "choix techniques".
Article de blog : pourquoi ELT, pourquoi DuckDB vs Postgres, pourquoi statique
vs serveur, ce que je referais différemment. Post LinkedIn. Lien sur le CV.
→ **Prêt pour les candidatures de septembre.**

### 2.7 Définition de "terminé" (Definition of Done)

- [ ] Le pipeline tourne seul depuis ≥ 2 semaines sans intervention
- [ ] `dbt build` : 0 erreur, ≥ 30 tests, tous verts
- [ ] Dashboard public accessible via une URL propre
- [ ] Lignage complet visible dans dbt docs
- [ ] README lisible par un non-initié en 3 minutes
- [ ] Article publié
- [ ] Un recruteur peut cloner le repo et tout lancer avec 3 commandes

### 2.8 Risques identifiés

| Risque | Impact | Parade |
|---|---|---|
| Rater la fenêtre live (finale 19/07) | Storytelling affaibli | Phase 1 en mode urgence ; fallback openfootball |
| Free tier API modifié | Pipeline cassé | Raw = filet de sécurité ; 3 sources indépendantes |
| IDs incohérents entre sources | Jointures qui droppent des lignes | Table de mapping explicite + tests dbt de volumétrie |
| Manque de temps (stage + recherche emploi) | Projet inachevé | Chaque phase livre un artefact montrable ; couper la V2, jamais la qualité |