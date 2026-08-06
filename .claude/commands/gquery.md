Interroge la carte Graphify sans jamais charger le graphe complet en contexte.

1. Si la CLI est disponible (`command -v graphify`), exécute :
   `graphify query "$ARGUMENTS"`
   (ajoute `--budget 1200` pour plafonner la sortie si besoin).
2. Sinon, invoque la skill `graphify` (outil Skill) avec la question : "$ARGUMENTS".

Analyse uniquement l'extrait renvoyé pour répondre. Ne fais jamais `cat graphify-out/graph.json` :
le JSON complet est une base de travail, pas un fichier à charger dans le contexte.
