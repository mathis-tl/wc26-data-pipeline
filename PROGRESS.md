# État du projet — wc26-data-pipeline

## Objectif du dernier sprint
« Le verdict à l'épreuve des chiffres réels (FBref, 48 équipes) » — session 1, backend/data uniquement, pas de dashboard.

## Réalisations terminées
- Dépendance `soccerdata` ajoutée au groupe `analytics`.
- `ingestion/fbref.py` : run-once (refuse de re-fetch sans `--force`), pull des 5 tables FBref (`INT-World Cup`, 2026) → `data/raw/fbref/team_basic_2026.csv` versionné (48 équipes × 13 colonnes).
- `analytics/real_fbref.py` : réconciliation noms FBref ↔ `dim_teams` via mapping explicite (6 divergences : Bosnia–Herz, Cabo Verde, Côte d'Ivoire, IR Iran, Korea Republic, Türkiye) ; échoue bruyamment dans les deux sens en cas de nom non résolu.
- `analytics/__main__.py` étendu : join réel FBref + `team_strength` du modèle → `dashboard/src/data/team_reality.json` (48 lignes : ranks/attack/defense modèle + possession/tirs/SoT/SoTA/GA/save%/CS/conversion réels).
- ADR 0006 écrit (`docs/adr/0006-fbref-basic-stats-no-xg-2026.md`) : source réelle basique, absence de xG 2026 documentée, discipline ADR-0004 étendue.
- Note `model_meta.json` nuancée : volumes de tir réels désormais disponibles, toujours aucun xG de tracking.
- Tests : `tests/test_fbref_reconcile.py` (4 tests unitaires + 1 `contract` : 0 non-apparié contre le vrai `dim_teams`) ; contrat d'export étendu (`team_reality.json` dans `tests/test_export_contract.py`).

## Fichiers impactés
- Nouveaux : `ingestion/fbref.py`, `analytics/real_fbref.py`, `tests/test_fbref_reconcile.py`, `docs/adr/0006-fbref-basic-stats-no-xg-2026.md`, `data/raw/fbref/team_basic_2026.csv`, `dashboard/src/data/team_reality.json`
- Modifiés : `analytics/__main__.py`, `tests/test_export_contract.py`, `docs/adr/README.md`, `pyproject.toml`, `uv.lock`, `.gitignore` (ignore `downloaded_files/`)
- Régénérés en effet de bord (re-run analytics) : `team_strength.json`, `rating_vs_finish.json`, `title_odds.json`, `title_progression.json`, `model_meta.json`, `data/ops/runs.jsonl` — bruit de dernier chiffre du solveur L-BFGS-B, sans rapport avec ce sprint.

## Décisions clés
- FBref choisi comme source #3 malgré l'absence de xG 2026 (vérifié : 5 tables basiques seulement, aucune colonne « Expected ») — apporte une réalité-check sur 48 équipes là où SofaScore ne couvre que l'Espagne.
- Mapping de noms explicite, pas de fuzzy matching — une dérive de nom doit échouer bruyamment, jamais se résoudre silencieusement vers le mauvais pays.
- Champ `conversion` (G/Sh) choisi plutôt que tout terme évoquant le xG, même si c'est une donnée de tir réelle (discipline ADR-0004 étendue à FBref).

## Validations effectuées
- `uv run python -m ingestion.fbref` : archive créée, re-run confirmé no-op (run-once).
- `uv run python -m analytics` : tourne sans erreur, `team_reality.json` généré.
- Vérification programmatique : 48 lignes, Espagne GA=1, save%=90.9, possession=64.1%, conversion=0.09, rank_defense=#1, rank_attack=#6.
- `uv run pytest -q` : 52 passed. `uv run pytest -m contract -q` : 20 passed, 1 failed (`upsets.json` sans contrat — préexistant, confirmé via `git stash` avant ce sprint, non lié).
- `uv run ruff check` + `uv run pyright` sur les fichiers touchés : propres.
- **Session 2 (front)** : le composant dashboard « réalité vs modèle » (section
  « Confirmé, à l'échelle du tournoi », Fig. 6 — scatter défense modèle × %
  d'arrêts réel FBref, `Takeaway` avec `r ≈ 0.75`) et sa note d'honnêteté
  (« aucun xG ne circule pour une compétition internationale 2026 ») étaient
  **déjà présents dans `index.astro`**, non commités, à la reprise de cette
  session — pas écrits par cette session, seulement retrouvés et validés.
  `npm run build` : propre. QA `shoot.mjs` (desktop 1280 + mobile 390, reduced-motion) :
  aucun débordement horizontal. Capture ciblée de la section Fig. 6 aux deux
  largeurs : rendu correct, labels (ESP/POR/IRN/GHA/COL) lisibles, pas de
  chevauchement.

## Risques / points ouverts
- `upsets.json` n'a toujours pas de contrat d'export (gap préexistant, hors scope de ce sprint).
- Rien n'est commité — modifications encore dans le working tree.

## Backlog (reporté, pas ce sprint)
- Revue éditoriale du texte narratif du dashboard (clarté du modèle statistique,
  chiffres non expliqués à proximité) — documentée dans `docs/BACKLOG.md`,
  **programmée en tout dernier**, après le reste de la roadmap produit.

## Prochaine étape exacte
Session 2 (front/récit) est validée (composant + note d'honnêteté + build + QA
desktop/mobile, voir ci-dessus) : plus de code à écrire pour ce sprint FBref.
Reste à décider avec l'utilisateur : committer l'ensemble du sprint (backend +
front), ou enchaîner sur autre chose avant de committer.
