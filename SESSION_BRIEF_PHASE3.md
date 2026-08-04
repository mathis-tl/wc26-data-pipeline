# Session : WC26 Pipeline — Phase 3 : dashboard public

## Rôles
Tu es l'exécutant technique. Architecture et direction artistique décidées en
amont (Mathis + Claude cerveau). Ce brief est prescriptif — en cas de doute,
demande à Mathis, n'improvise pas. Rituel inchangé : Graphify → diagnostic →
proposition → validation → implémentation. Fin de session : carte Graphify
régénérée + addendum SESSION_NOTES.md.

## Tâche zéro — maintenance & skills
1. La carte Graphify est fragmentée (56 arêtes orphelines, mismatch d'IDs
   entre extracteurs). Rebuild complet propre AVANT toute chose.
2. **Skill `frontend-design` OBLIGATOIRE** (skill officiel Anthropic —
   installe-le depuis anthropics/skills s'il n'est pas déjà présent).
   Applique sa méthode en deux passes À LA LETTRE : plan de design
   (palette hex nommée, rôles typographiques, wireframes ASCII, élément
   signature) → auto-critique anti-générique → validation Mathis → code.
   Auto-critique par screenshots pendant le build.

## Décision d'architecture : Evidence est ABANDONNÉ
Le plan initial prévoyait Evidence. Décision actée avec le cerveau : exigence
de design distinctif → front custom. L'architecture reste 100% statique :

```
dbt marts (DuckDB) ──export──► JSON (dashboard/src/data/)
                                    │ build front (aucune dépendance Python)
                                    ▼
                              site statique ──► Vercel (intégration Git)
```

- Framework : **Astro** + islands React uniquement si interactivité requise
  (bracket). Zéro JS shippé par défaut. Mathis maîtrise React/TS.
- Export des marts : step dans le workflow quotidien existant — DuckDB
  `COPY (SELECT ...) TO '...json'` pour chaque mart exposé. Les JSON sont
  commités par la même PR auto quotidienne que le raw. Le front ne dépend
  JAMAIS de Python/dbt pour se builder.
- Déploiement : intégration Git Vercel sur `main` (compte Vercel : Mathis —
  il connecte le repo lui-même, prévois juste `vercel.json` si nécessaire
  et le répertoire de build). Chaque merge (code OU données du matin)
  redéploie automatiquement. Pas de CLI, pas de token en CI.

## Direction artistique — hybride "éditorial + terminal" (STRICT)
Référence : structure éditoriale type The Pudding / The Athletic, composants
data type écran de timing. Le site se lit comme un rapport visuel du tournoi,
de haut en bas.

### Design system imposé
- **Fond clair papier** (blanc cassé, pas de blanc pur), encre quasi-noire.
- **2 fontes MAXIMUM** : une serif display à fort caractère pour titres et
  gros chiffres (propose 2-3 options open source à Mathis : type Fraunces,
  Instrument Serif...) + une monospace pour TOUTES les données chiffrées,
  tables, timestamps (type IBM Plex Mono, JetBrains Mono). Corps de texte :
  la serif ou une system stack neutre — pas de 3e fonte décorative.
- **1 seule couleur d'accent** (propose 2-3 options à Mathis). Tout le reste
  en nuances d'encre/papier.
- **Bandeau de fraîcheur** en haut de chaque page, style terminal :
  `dernière ingestion 2026-07-13 06:04 UTC · dbt build 46/46 ✓ · source:
  football-data.org` — généré depuis les métadonnées d'export. La rigueur
  pipeline devient un élément de design.
- Tables denses, alignement numérique strict (tabular-nums), lignes fines.
- Gros chiffres éditoriaux (buts, matchs, équipes) en très grand corps serif.

### Interdictions absolues (anti-slop)
- Aucun dégradé (surtout violet/bleu), aucun glassmorphism, aucune ombre
  portée décorative, pas de cards arrondies génériques, pas d'emoji dans
  l'UI, pas d'icônes décoratives sans fonction, pas de hero vide avec
  tagline marketing, pas de dark mode en V1 (une seule identité, maîtrisée).
- Si un composant ressemble à un template Tailwind par défaut : refais-le.
- **Singularisation vs les 3 clichés IA du skill frontend-design** : notre
  direction (papier + serif + éditorial) est ADJACENTE aux défauts n°1 et
  n°3 que le skill identifie. Conséquences : accent terracotta/argile
  INTERDIT (zone #D97757 et voisins — c'est le marqueur IA n°1) ; le
  caractère du site doit venir de nos éléments signature PROPRES AU SUJET
  (bandeau fraîcheur terminal, photos duotone, bracket, chiffres géants),
  pas d'un habillage "journal" générique. Applique le test du skill : si
  un autre brief similaire donnerait le même résultat, révise.

### Motion (épuré, orchestré — pas dispersé)
- UN moment orchestré maximum par page (ex : compteur des chiffres-clés à
  l'entrée dans le viewport, ou révélation progressive du bracket) — c'est
  la règle du skill : un moment qui marque > des effets partout.
- Scroll-reveals éditoriaux subtils autorisés (fade/translate courts,
  déclenchés à l'entrée dans le viewport, jamais rejoués), inspiration
  scrollytelling sobre type The Pudding. Pas de parallax, pas de glow/néon,
  pas d'animations en boucle, pas d'effets au scroll qui détournent du
  contenu.
- `prefers-reduced-motion` respecté partout (le skill l'exige, et c'est
  un signal de sérieux pour un recruteur qui inspecte).

### Assets visuels — règles LÉGALES non négociables
- Photos : dans /Users/mathistelle/Pipeline_WC/assets
- Traitement systématique : **duotone dans la palette du site** (script de
  build ou CSS blend) — aucune photo brute. C'est le traitement qui fait
  l'identité, pas la photo.
- Écussons équipes : URLs `crest` fournies par l'API (déjà dans le raw),
  affichés en petit dans tables et bracket.
- Footer : crédits photos (auteur + source), sources de données, lien repo
  + dbt docs.

## Pages (dans cet ordre de priorité)
1. **Accueil — le récit du tournoi** : chiffres-clés géants (matchs joués,
   buts, etc. depuis fct_matches), derniers résultats, prochains matchs
   (demies 14-15/07, finale 19/07), bandeau fraîcheur.
2. **Groupes** : les 12 groupes depuis fct_group_standings, qualification
   surlignée, mention discrète « classement recalculé depuis les résultats
   bruts — réconcilié 48/48 avec l'officiel » (l'argument portfolio).
3. **Phase finale** : bracket LAST_32 → FINAL depuis fct_matches.
   Desktop : horizontal. Mobile : empilé verticalement, cards de match
   extensibles (les brackets horizontaux s'effondrent sur mobile — décision
   de recherche, pas de débat).
4. **Méthodo / À propos** : schéma du pipeline, lien repo, stack, le test
   de réconciliation expliqué en 3 phrases. Page courte mais c'est celle
   que les recruteurs liront.
Hors scope V1 : comparaisons historiques (post-backfill), top buteurs
(nécessite l'endpoint /scorers — extension d'ingestion possible, à vérifier
sur le free tier, NE PAS bloquer la phase là-dessus).

## Intégration & qualité
- CI de PR étendue : lint front + build Astro. Le build front doit passer
  sans réseau (données = JSON commités).
- Perf : site statique → vise Lighthouse ≥ 95 partout. Images optimisées
  (formats modernes, tailles adaptées), fontes en self-host subset.
- Responsive mobile d'abord vérifié sur les 4 pages — le lien sera ouvert
  depuis LinkedIn, donc majoritairement sur téléphone.
- Accessibilité de base : contrastes AA, tables avec vrais <th>, alt text.
- Micro-chantiers hérités de la Phase 2 à inclure : moderniser la syntaxe
  des 16 tests génériques dépréciés ; documenter dans le README les
  commandes exactes de reproduction (`dbt build --project-dir dbt
  --profiles-dir dbt` depuis la racine) ; label automatique `data` sur les
  PRs quotidiennes du bot + note README pour filtrer (`is:pr -label:data`).

## Jalon
Objectif : dashboard EN LIGNE avant la finale du 19/07. Les demies des
14-15/07 doivent apparaître via le run quotidien sans intervention humaine.
Priorité si le temps manque : Accueil + Groupes en ligne > tout le reste.

Commence par la tâche zéro (Graphify), puis propose : (a) le squelette
Astro + le step d'export JSON, (b) 2-3 propositions de palette + fontes
en mockup statique d'UNE section (le bandeau fraîcheur + un bloc de
chiffres-clés) pour validation de Mathis AVANT de générer le reste.
N'écris aucun composant définitif avant validation de la direction.