Clôture le sprint. Mets à jour `PROGRESS.md` à la racine — court, factuel, actionnable.

Structure attendue :

```
# État du projet — <nom>

## Objectif du dernier sprint
Une seule phrase.

## Réalisations terminées
Fonctionnalités ou corrections réellement finies (pas « en cours »).

## Fichiers impactés
`chemin/fichier.ext`

## Décisions clés
Décision + raison.

## Validations effectuées
Commande réellement exécutée + résultat. Ne prétends jamais qu'un test a tourné sans l'avoir lancé.

## Risques / points ouverts
Problème concret encore présent.

## Prochaine étape exacte
Une seule tâche actionnable.
```

Règles : reste bref, n'y mets pas ce qui est déjà dans Git/les logs.
Puis, si `graphify` est installé (`command -v graphify`), lance `graphify update .` pour rafraîchir la carte (incrémental).
Enfin, rappelle-moi de faire `/clear` pour repartir sur un contexte propre.
