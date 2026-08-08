# Backlog — sprints identifiés, pas encore programmés en priorité

Sprints relevés et documentés pour ne pas perdre le contexte, mais **volontairement
reportés**. Chaque entrée porte sa position voulue dans la roadmap.

---

## Revue éditoriale du texte narratif (dashboard) — À TRAITER EN TOUT DERNIER

> Positionnement explicite : après tous les autres sprints prévus (dashboard
> « réalité vs modèle », et tout ce qui suivra). C'est une passe de clarté sur un
> texte déjà en ligne, pas une fonctionnalité bloquante — ne pas l'avancer avant
> que le reste de la roadmap produit soit livré.

### Origine

Relevé le 2026-08-08 en relisant `dashboard/src/pages/index.astro` (section
« Analyse » et section méthode). Le récit utilise « modèle statistique », « note
de force », « points attendus (xPts) », « probabilité de victoire / de titre »
abondamment dès le haut de page, sans que le lecteur sache d'où sortent ces
chiffres avant d'arriver — ~700 lignes et 5 sections plus loin — à la section
méthode, qui elle-même ne couvre pas tout.

### Constat vérifié (pas une hypothèse à re-checker)

Les chiffres sont **réels et traçables jusqu'au code**
(`analytics/model.py` : modèle Poisson attaque/défense ajusté par maximum de
vraisemblance + pénalité ridge, puis simulation Monte-Carlo du tableau à élimination
directe). Le problème n'est **pas** la fabrication de données : c'est un
**défaut de séquençage éditorial** — la définition arrive trop tard, et une fois
là-bas, elle reste incomplète sur un maillon précis.

### Problèmes recensés (exhaustif)

**A. Le modèle est utilisé ~500 lignes avant d'être défini.** « Un modèle
statistique » apparaît ligne 250 (section Analyse, en haut de page). Sa
définition réelle (`log E[buts] = attaque − défense + terrain`, ajustement par
MLE + ridge) n'apparaît que ligne ~958-975, dans la section `id="methode"`, qui
vient après Analyse, Chiffres, Buteurs, Groupes **et** Bracket.

**B. Les renvois « expliqué plus bas » ne sont pas cliquables.** Trois
occurrences (lignes ~338-339, ~515-516, ~701-702 au moment de cette revue)
promettent une explication « plus bas, dans la section méthode » en texte brut,
sans `<a href="#methode">`, alors que la section a bien un ancrage `id="methode"`.

**C. Le glossaire d'ouverture (« Comment lire ce rapport », lignes ~278-298) est
incomplet.** Il définit 4 termes (Note de force, Attaque/Défense, xPts, xG
modèle/réel) mais pas « probabilité de victoire » ni « probabilité de titre »,
pourtant les deux statistiques les plus citées de la page (53 %, 78 %, 46 %, et
tout le graphique Fig. 4). Même quand un terme y est défini, c'est une définition
de la grandeur dérivée, pas une explication du calcul.

**D. Le maillon le plus important n'est expliqué nulle part, même dans la
section méthode.** Vérifié dans `analytics/model.py:113-139` : la probabilité
de victoire d'un match sort de deux lois de Poisson indépendantes (buts
domicile / extérieur) combinées en une matrice de scores (`score_matrix`), puis
sommées par triangle (`outcome_probs` : triangle inférieur = victoire domicile,
trace = nul, triangle supérieur = victoire extérieur). Ce passage « attaque/
défense → probabilité de victoire d'un match précis » n'est écrit **nulle part**
dans le texte, pas même dans la section méthode qui ne couvre que (1) le modèle
de buts et (2) la simulation du tournoi à partir de probabilités déjà données.

**E. Affirmations comparatives non vérifiables en l'état.** Ex. : « 6ᵉ plus gros
écart positif du tournoi, dans la même fourchette que la Suisse ou le Paraguay »
(ligne ~425-427) — le rang est calculé (`performanceRank`) mais les valeurs de la
Suisse et du Paraguay ne sont données nulle part dans le texte ; il faut les lire
soi-même sur le graphique Dumbbell (Fig. 2) juste en dessous. Idem pour
« 6 fois plus souvent que Colombia » (`runnerUpRatio`).

**F. Le modèle n'est jamais nommé en clair avant sa mention tardive.** La page
n'utilise « Poisson, maximum de vraisemblance » qu'à la ligne ~694 — un aparté
dès la première mention (« un modèle statistique — une régression de Poisson qui
attribue à chaque équipe une force d'attaque et une force de défense, détails
plus bas ») désamorcerait une bonne partie de la confusion sans déplacer aucune
section.

*(Point G relevé mais explicitement pas un problème : la note sur le label
« domicile » ligne ~735 est un bon exemple de nuance honnête déjà bien faite —
sert de référence pour le ton à reproduire ailleurs.)*

### Problème majeur

Un défaut de **séquençage éditorial**, pas de fabrication de chiffres. Un
lecteur qui lit dans l'ordre rencontre : jargon non défini → chiffres non
expliqués → un glossaire partiel → encore des chiffres → puis, 700 lignes plus
loin, une explication qui répond à « comment le modèle de buts est ajusté » et
« comment le tournoi est simulé », mais pas à « comment on obtient une
probabilité de victoire pour un seul match » — la statistique la plus citée du
texte. Résultat : la page paraît accumuler des affirmations chiffrées non
sourcées, alors que la source existe — elle est juste mal placée et
partiellement incomplète. C'est un problème de confiance du lecteur, pas de
justesse des données.

### Solution proposée (3 leviers, cumulables)

1. **Rapprocher, pas réécrire** : dupliquer en résumé (formule attaque/défense)
   directement dans la section Analyse, juste après la première mention de
   « modèle statistique » (~ligne 250). La section méthode complète reste à sa
   place pour le lecteur qui veut le détail du pipeline et de la simulation.
2. **Combler le trou réel** : ajouter une phrase (formule courte si besoin)
   expliquant explicitement buts → probabilité de match (matrice de Poisson
   indépendante, triangle inf/sup/trace). C'est le seul maillon jamais écrit,
   dans aucune section.
3. **Ancrer et compléter le glossaire** : transformer les 3 « expliqué plus
   bas » en vrais liens `<a href="#methode">`, et ajouter « probabilité de
   victoire / de titre » au bloc « Comment lire ce rapport ».

### Fichiers concernés

- `dashboard/src/pages/index.astro` — tout le texte narratif + structure des
  sections (fichier unique qui gère l'affichage du texte sur le site).
- `analytics/model.py` — source de vérité du calcul, à relire pour rédiger
  correctement le maillon manquant (buts → probabilité de match), lignes
  113-139 (`score_matrix`, `outcome_probs`).

### Definition of Done

- [ ] Première mention de « modèle statistique » (section Analyse) immédiatement
      suivie d'une explication concrète (au moins la formule attaque/défense).
- [ ] Le maillon « buts → probabilité de victoire d'un match » est écrit en
      clair quelque part dans la page.
- [ ] Le glossaire « Comment lire ce rapport » inclut « probabilité de
      victoire » et « probabilité de titre ».
- [ ] Les 3 renvois « expliqué plus bas » sont des ancres cliquables vers
      `#methode`.
- [ ] Relecture complète de la page pour vérifier qu'aucun chiffre cité ne
      reste sans mécanisme visible à proximité raisonnable.
- [ ] `npm run build` + QA visuelle (`shoot.mjs`, desktop + mobile 390).

### Prompt de démarrage (à copier tel quel le moment venu)

```
Sprint : revue éditoriale du texte narratif du dashboard (clarté du modèle statistique).

Contexte : dashboard/src/pages/index.astro raconte "l'Espagne a-t-elle mérité son
titre ?" en citant beaucoup de chiffres du modèle (note de force, xPts, probabilité
de victoire/titre) sans que leur origine soit expliquée à proximité. La section
méthode existe (id="methode") mais arrive ~700 lignes après la première mention du
"modèle statistique", et même là elle n'explique pas comment on passe des forces
attaque/défense à une probabilité de victoire d'un match (ce maillon vit uniquement
dans analytics/model.py:113-139, score_matrix + outcome_probs — jamais écrit en
prose nulle part).

Analyse complète déjà faite, NE PAS LA REFAIRE : lis docs/BACKLOG.md, section
"Revue éditoriale du texte narratif (dashboard)" — liste exhaustive des problèmes
A à F, problème majeur, solution en 3 leviers.

Objectif de cette session :
1. Rapprocher la définition du modèle (formule attaque/défense) de sa première
   mention dans la section Analyse, sans dupliquer toute la section méthode.
2. Écrire en clair le maillon manquant : buts (Poisson) → probabilité de victoire
   d'un match, quelque part dans la page (section Analyse et/ou méthode).
3. Compléter le glossaire "Comment lire ce rapport" avec "probabilité de
   victoire" et "probabilité de titre".
4. Transformer les 3 renvois texte "expliqué plus bas" en ancres <a href="#methode">.
5. Relire toute la page une fois les changements faits pour vérifier qu'aucun
   chiffre cité (xPts, %, rangs comparatifs) ne reste sans mécanisme visible à
   proximité raisonnable.

Garde-fous : ne change aucun chiffre ni aucune donnée, uniquement l'exposition /
structure du texte ; garde le ton éditorial existant (measure/prose, howto, etc.) ;
pas de commit/push sans demande explicite ; réponds en français ; QA visuelle
(npm run build + shoot.mjs desktop/mobile 390) avant de considérer terminé.
```
