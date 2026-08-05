# Plan — prochaine session : accompagner le lecteur, clôturer le récit

Synthèse de trois revues externes (relues au bistouri : elles ont été faites
**sans exécuter le site**, donc une bonne part de leurs conseils tombe à côté).
Ce plan ne garde que ce qui survit à une revue *sur le site réel*.

## Contexte

Le pipeline et le writing sont jugés très bons (revues : « 9.5/10 », « digne du
NYT Upshot / The Athletic », « pas de la merde »). Ce qui bride le dashboard
n'est **ni la donnée ni les visuels**, mais le fait qu'il est écrit par
quelqu'un qui connaît déjà ses chiffres : un lecteur extérieur a besoin qu'on
lui dise *que montre ce graphe, pourquoi, quoi retenir*. Et le récit **ne se
referme pas** (la page finit sur la méthode).

## Ce qui est REJETÉ (et pourquoi — à assumer, pas à corriger)

Tout l'attirail « analytics joueurs » demandé par les revues suppose de la
donnée événementielle par joueur (StatsBomb/Opta) que ce projet **n'a pas**, par
conception : c'est un modèle **par équipe** sur des scores + du xG réel limité à
l'Espagne. À rejeter en bloc, car les fabriquer détruirait le seul atout le plus
fort du projet — l'honnêteté méthodologique :

- per-90 / percentiles, comparaison par poste, filtres poste/saison/ligue/temps
  de jeu → pas de donnée joueur.
- PPDA, PrgP, xThreat, npxG, radars / pizza charts → pas de donnée de tracking.
- « préciser la source du xG » → **déjà fait** (football-data = scores ;
  SofaScore = xG réel Espagne ; « jamais appelé xG »).

Déjà présents mais non vus par les reviewers (ne rien refaire) : formule Poisson
+ code `fit()`/`play()` (« Le modèle, à nu »), section limites (« Ce que le
modèle ne fait pas »), PipelineDiagram + StarSchema + ReconciliationDiagram,
traçabilité des sources.

## Tier 1 — les vrais trous (3 revues ont convergé dessus)

### 1. Le lecteur ne sait pas lire les chiffres → pédagogie des métriques
Devant `Att. 0.80 · Déf. 2.48 · Note 3.27`, aucun repère d'échelle. À ajouter :
- Un encadré **« Comment lire ce rapport »** en tête de l'essai (ou repliable) :
  Note de force (0 = équipe moyenne, échelle log-buts), Att./Déf. (plus haut =
  mieux, y compris la défense — piège actuel : Déf. 2.48 « élevé » = bon), Pts
  attendus (xPts), xG modèle vs xG réel.
- Des **définitions au survol** (tooltip ou petit `i`) sur chaque terme technique
  à sa première occurrence : note de force, xPts, xG modèle. Composant réutilisable
  `<Term def="…">note de force</Term>`.
- **Piège à corriger absolument** : dans le tableau de notes, un œil naïf lit
  « Espagne Att. 0.80 » et croit l'attaque faible vs Angleterre 1.21 — il faut
  soit une légende, soit afficher le rang à côté (#6 attaque) pour lever
  l'ambiguïté. C'est le point n°1 des trois revues.

### 2. Les KPIs d'intro ne racontent rien → contexte dérivé (réel, pas inventé)
Les 4 gros nombres (104/333/48/3.20) sont bruts. On a désormais
`mart_edition_comparison` pour les faire parler **avec de la vraie donnée** :
- 104 matchs → « +28 vs 2022 » (format élargi)
- 333 buts → à situer historiquement
- 48 équipes → « 1ʳᵉ édition à 48 »
- 3.20 buts/match → « meilleure moyenne depuis 1958 » (déjà calculé plus bas,
  juste à remonter sous le KPI)
Ajouter une ligne de contexte sous chaque `stat__value` (dérivée du mart, pas
en dur). Relie aussi le KPI à la section historique existante.

### 3. Pas de conclusion → clôture éditoriale
La page finit sur méthode + stack + GitHub. Ajouter une **section de clôture**
avant le footer qui synthétise : la place de cette Espagne dans l'histoire (lien
au 7ᵉ/23), le verdict du modèle en une phrase, 2–3 records/surprises du tournoi
(meilleur buteur, plus gros upset — déjà dans les marts `upsets`/`top_scorers`),
et une dernière ligne éditoriale. Courte, pas un pavé.

## Tier 2 — accompagner le lecteur figure par figure

### 4. « À retenir » sous chaque figure des sections annexes
L'essai `#analyse` interprète déjà bien. Les sections annexes (chiffres,
buteurs, groupes) sont plus descriptives. Ajouter une ligne **« À retenir : … »**
(ou une phrase de lecture avant) sous chaque graphe pour dire quoi en tirer —
pas un paragraphe, une phrase.

### 5. Scatter Fig 1 — lisibilité
Réel, pas « anonyme » (il labelle déjà ESP/POR/ARG/BEL/ENG + lignes médianes),
mais :
- collisions de labels à régler : ARG/BEL se chevauchent, ENG collé au label
  d'axe « Attaque ».
- labelliser les **outliers intéressants** (Angleterre = meilleure attaque à
  droite ; l'anomalie en bas ; pas seulement le top-5 par note).
- éventuel trait de rappel (leader line) sur les points denses.

### 6. Réconciliation des DEUX sources, valorisée
Le ReconciliationDiagram actuel parle du **calcul des classements** (computed vs
official). La réconciliation **SofaScore ↔ football-data sans ID commun**
(matching chronologique par équipe + date) n'est qu'évoquée en prose. En faire
un petit schéma/encadré : c'est une problématique Data Engineering très
concrète et valorisante. (`analytics/real_stats.py` a déjà la logique.)

## Tier 3 — renforcer le signal DE (si le temps)

- Rendre le PipelineDiagram plus explicitement « DAG source→…→front » nommant
  les **deux** sources et l'étape de réconciliation.
- Vérifier le scroll horizontal + en-têtes des tables larges sur mobile
  (heatmap surtout).
- Glossaire complet en bas de la section méthode (repli).

## Note de cadrage

Ne pas retomber dans le piège inverse : ce projet gagne par la **retenue et
l'honnêteté**, pas par l'empilement de features. Chaque ajout ci-dessus sert le
lecteur ou le récit ; rien n'invente de donnée. Le fil directeur reste
« montrer la machinerie, honnêtement ».
