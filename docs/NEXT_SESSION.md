# Plan — prochain sprint : le verdict à l'épreuve des chiffres réels (FBref, 48 équipes)

> Sprint 1 (accompagnement lecteur + clôture) est **livré et déployé**. Cette session
> a exploré l'enrichissement par une source foot externe. Conclusions **vérifiées par
> la donnée**, pas supposées — les voici pour ne pas refaire le chemin.

## Ce qui a été vérifié cette session (NE PAS re-chercher)

- ✅ **FBref via `soccerdata`** (league `"INT-World Cup"`, season `2026`) charge les **48
  équipes** ; Cloudflare est percé par soccerdata (`wrapper-tls-requests`).
- ❌ **FBref n'a AUCUN xG pour la WC 2026.** Prouvé : pour les compétitions internationales
  soccerdata n'expose que 5 tables **basiques** (`standard`, `keeper`, `shooting`,
  `playing_time`, `misc`) et **aucune** ne contient de colonne « Expected ». Les pages xG
  de FBref existent pour 2022 (StatsBomb), **pas 2026**. → **Ne pas re-tenter le xG via FBref.**
- ❌ **xG réel des 48 équipes = nulle part gratuit ET propre.** SofaScore l'a (c'est la
  source du xG Espagne) mais le plan RapidAPI **gratuit = 50 req/mois < ~105 requis**
  (→ tier payant) ; le direct `api.sofascore.com` est ToU-gris. API-Football (`expected_goals`,
  free 100/j) **non vérifié** — piste si un jour on veut le vrai xG.
- ✅ **Ce qu'on garde : FBref basique** — vrai, gratuit, fiable, buildable maintenant.

## Objectif du sprint

**« Le verdict à l'épreuve des chiffres réels »** : confronter les notes du modèle Poisson
au réel FBref sur 48 équipes — domination au tir, mur défensif, conversion. **Pas du xG** :
un contrôle de réalité honnête au niveau équipe.

## Pourquoi ça vaut le coup (chiffres Espagne réels, déjà tirés)

| Volet thèse | Le modèle disait | Le réel FBref confirme |
|---|---|---|
| Mérite — défense | « Défense #1 » | **1 but encaissé en 8 matchs**, 11 TC concédés, **90.9 % d'arrêts** |
| Mérite — contrôle | rating élevé | **64.1 % possession**, 140 tirs (16.8/90) |
| Chance — finition | « facteur +2.16 » | **G/Sh 0.09** → pas de sur-conversion : gagné par la défense, pas la veine |

Renfort du verdict **plus fort qu'espéré**, et gratuit.

## Données disponibles (48 équipes, agrégats tournoi)

Tirs, tirs cadrés, SoT%, G/Sh, G/SoT, possession, buts/passes, **gardien** (GA, GA90, SoTA,
arrêts, save%, clean sheets, W/D/L), cartons/fautes/interceptions/hors-jeu.
**Non dispo : xG, passes progressives, per-match.**

## Architecture — calque le chemin SofaScore, PAS un mart dbt

Le réel vit dans la couche **Python `analytics/`** (dbt = scores/standings/buteurs).

1. **Dépendance** : `uv add --group analytics soccerdata` (déjà installé en jetable dans `.venv`).
2. **Acquisition** : `ingestion/fbref.py` sur le modèle de `ingestion/sofascore.py` — run-once,
   refuse de re-fetch si l'archive existe (sauf `--force`), pull des 5 tables, garde les
   colonnes utiles → `data/raw/fbref/team_basic_2026.csv` **versionné** (ADR 0001).
3. **Réconciliation noms** FBref ↔ `dim_teams` — **LE risque du sprint**. Cible : **0 non-apparié
   sur 48** (mapper Korea Republic, IR Iran, Cabo Verde, Türkiye, etc.).
4. **Comparaison** : `analytics/` joint le réel au `team_strength` du modèle → exporte
   `dashboard/src/data/team_reality.json` (par équipe : `rank_overall/attack/defense` du modèle
   + tirs, SoTA, GA, save%, conversion, possession réels).
5. **Dashboard** (session 2) : composant « réalité vs modèle ».

## Garde-fous / conformité

- Nouvel **ADR 0006** — « FBref (soccerdata) comme source de stats *basiques* réelles :
  run-once, raw versionné, **absence de xG pour 2026 documentée** ».
- **ADR 0004 maintenu** : ne jamais appeler « xG » la sortie du modèle. Nuancer la note de
  `model_meta.json` : on a désormais des **volumes de tir réels**, mais toujours **pas de xG
  de tracking** — la distinction reste nette.
- **Tests** : réconciliation des noms (0 non-apparié) + contrat d'export (cf. `tests/test_export_contract.py`).

## Découpage

- **Session 1 (backend/data)** : dép + `ingestion/fbref.py` + réconciliation + join analytics +
  export `team_reality.json` + ADR 0006 + tests. Aucun dashboard.
- **Session 2 (front/récit)** : composant dashboard + note d'honnêteté + QA `npm run build` +
  `shoot.mjs` (desktop + mobile 390).

## Definition of Done (sprint)

- [x] `data/raw/fbref/team_basic_2026.csv` versionné ; `ingestion/fbref.py` reproductible, run-once.
- [x] `team_reality.json` : 48 équipes, **0 non-apparié**, chiffres Espagne cohérents (1 GA, 90.9 %).
- [x] Composant dashboard « réalité vs modèle » en ligne, labels honnêtes (ADR 0004).
- [x] ADR 0006 écrit ; note `model_meta.json` nuancée ; tests verts ; build + QA mobile OK.

## Hors scope (décidé)

xG (indisponible pour 2026), passes prog / style (**Sprint C** optionnel), analytics joueur
(**Sprint B** optionnel, via API-Football — nécessite un ADR qui acte le revirement).

---

## Prompt de démarrage — session 1

```
Sprint : « Le verdict à l'épreuve des chiffres réels (FBref, 48 équipes) ».
Commence par lire docs/NEXT_SESSION.md — surtout la section « vérifié cette session » :
FBref n'a PAS de xG pour 2026, c'est prouvé, ne le re-cherche pas.

Objectif de CETTE session : backend/data uniquement. Faire entrer les stats FBref
réelles dans le pipeline et produire le JSON de comparaison modèle↔réel. Pas de dashboard.

Étapes, dans l'ordre :
1. Dépendance : `uv add --group analytics soccerdata` (déjà installé en jetable dans .venv).
2. `ingestion/fbref.py` calqué sur `ingestion/sofascore.py` : run-once, refuse de re-fetch
   si l'archive existe (sauf --force) ; pull des 5 tables FBref (league "INT-World Cup",
   season 2026) ; garde tirs, SoT, SoT%, G/Sh, possession, GA, SoTA, saves, save%, CS,
   cartons ; écrit data/raw/fbref/team_basic_2026.csv versionné (ADR 0001).
3. Réconcilie les noms FBref ↔ dim_teams — c'est LE risque. DoD = 0 non-apparié sur 48
   (Korea Republic, IR Iran, Cabo Verde, Türkiye…). Fais un mapping explicite et testé.
4. Étends analytics/ : joins le réel au team_strength du modèle → exporte
   dashboard/src/data/team_reality.json (par équipe : rank_overall/attack/defense du
   modèle + tirs, SoTA, GA, save%, conversion, possession réels).
5. ADR 0006 (FBref basique, run-once, raw versionné, absence de xG documentée). Nuance la
   note de model_meta.json (volumes de tir réels ≠ xG tracking ; jamais appelé « xG »).
6. Tests : réconciliation noms (0 unmatched) + contrat d'export.

Garde-fous : discipline ADR 0004 (jamais « xG » pour le model-output) ; pas de commit/push
sans demande explicite ; réponds en français ; interroge la carte via /gquery, pas le JSON brut.

Vérification de fin de session : lance l'analytics, montre-moi que team_reality.json a 48
lignes, 0 non-apparié, et que les chiffres Espagne (1 GA, 90.9 % save%, 64 % possession)
apparaissent bien.
```
