#!/usr/bin/env bash
# ============================================================================
# Kit Claude Code — micro-sprints + Graphify   (version adaptée, tout projet)
# ----------------------------------------------------------------------------
# Idempotent et NON destructif : merge settings.json, remplace uniquement son
# bloc balisé dans CLAUDE.md, sauvegarde tout fichier modifié dans .claude/backups/.
# Fonctionne que `graphify` soit une CLI OU une skill (le hook no-op sinon).
#
#   chmod +x setup-claude.sh && ./setup-claude.sh
# ============================================================================
set -euo pipefail

ROOT="$(pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
BK=".claude/backups/$STAMP"
mkdir -p .claude/commands "$BK"

backup() { [ -f "$1" ] && cp "$1" "$BK/$(echo "$1" | tr '/' '_')" || true; }

# --- 1. settings.json : merge (jamais d'écrasement) -------------------------
backup ".claude/settings.json"
python3 - "$ROOT/.claude/settings.json" <<'PY'
import json, sys
from pathlib import Path
p = Path(sys.argv[1])
cfg = json.loads(p.read_text()) if p.exists() else {}
hooks = cfg.setdefault("hooks", {})
ss = hooks.setdefault("SessionStart", [])
cmd = "cat PROGRESS.md 2>/dev/null || echo 'Pas de PROGRESS.md — lance /sprint-end pour en créer un.'"
def has(cmd):
    for grp in ss:
        for h in grp.get("hooks", []):
            if h.get("command", "").startswith("cat PROGRESS.md"):
                return True
    return False
if not has(cmd):
    ss.append({"hooks": [{"type": "command", "command": cmd}]})
p.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
print("settings.json : hook SessionStart -> PROGRESS.md OK")
PY

# --- 2. Commandes de sprint (fichiers gérés par le kit) ---------------------
cat > .claude/commands/sprint-start.md <<'EOF'
Reprends le sprint en cours sans recharger tout l'historique.

1. Lis `PROGRESS.md` s'il existe.
2. Exécute `git status --short` puis `git log --oneline -5`.
3. Si `graphify-out/graph.json` existe, note la présence de la carte — ne la régénère pas.
4. Synthèse en 3 puces : dernier sprint / état Git / tâche prioritaire (« Prochaine étape »).

Attends ma validation de l'objectif avant de coder.
EOF

cat > .claude/commands/sprint-end.md <<'EOF'
Clôture le sprint. Mets à jour `PROGRESS.md` (court, factuel) avec : Objectif, Réalisations
terminées, Fichiers impactés, Décisions clés, Validations réellement exécutées, Risques,
Prochaine étape exacte (une seule tâche).

Ne prétends jamais qu'un test a tourné sans l'avoir lancé. Si `graphify` est installé,
lance `graphify update .`. Puis rappelle-moi de faire `/clear`.
EOF

cat > .claude/commands/gquery.md <<'EOF'
Interroge la carte Graphify sans charger le graphe complet.

1. Si `command -v graphify` : `graphify query "$ARGUMENTS"` (option `--budget 1200`).
2. Sinon : invoque la skill `graphify` avec "$ARGUMENTS".

Analyse seulement l'extrait renvoyé. Ne fais jamais `cat graphify-out/graph.json`.
EOF

cat > .claude/commands/review-change.md <<'EOF'
Fais relire le diff courant dans un contexte isolé avant de committer.
Invoque la skill `code-review` sur la branche courante ; rapporte les problèmes actionnables,
du plus grave au moins grave. Ne réécris rien tant que je n'ai pas tranché.
EOF

cat > .claude/commands/context-health.md <<'EOF'
Diagnostic du contexte en 1-2 lignes : CONTINUER (objectif unique/cohérent) ;
/compact (sprint non fini mais session longue) ; /sprint-end + /clear (objectif atteint,
changement de sujet, sujets mélangés, contexte répétitif).
EOF
echo "commandes /sprint-start /sprint-end /gquery /review-change /context-health écrites"

# --- 3. Hook git post-commit : ré-indexation incrémentale -------------------
HOOK=".git/hooks/post-commit"
SNIP='if command -v graphify >/dev/null 2>&1; then\n  graphify update . >/dev/null 2>&1 &\nfi'
if [ -d .git ]; then
  if [ -f "$HOOK" ] && ! grep -q "graphify update" "$HOOK"; then
    backup "$HOOK"; printf '\n# CLAUDE-KIT\n%b\n' "$SNIP" >> "$HOOK"
    echo "post-commit : snippet graphify ajouté au hook existant"
  elif [ ! -f "$HOOK" ]; then
    printf '#!/bin/sh\n# CLAUDE-KIT: ré-indexation Graphify incrémentale en arrière-plan.\n%b\n' "$SNIP" > "$HOOK"
    echo "post-commit : hook créé"
  else
    echo "post-commit : déjà en place"
  fi
  chmod +x "$HOOK"
else
  echo "post-commit : pas de dépôt git, ignoré"
fi

# --- 4. CLAUDE.md : bloc balisé (remplacé, jamais dupliqué) -----------------
backup "CLAUDE.md"
python3 - "$ROOT/CLAUDE.md" <<'PY'
import re, sys
from pathlib import Path
p = Path(sys.argv[1])
block = """<!-- CLAUDE-KIT:START (bloc géré par setup-claude.sh) -->
## Workflow par micro-sprints
- Reprise : `/sprint-start`. Clôture : `/sprint-end` puis `/clear`.
- Architecture/dépendances : `/gquery "<question>"` — jamais `cat graphify-out/graph.json`.
- Revue avant commit : `/review-change`. Contrôle : `/context-health`.

## Graphify
- Jamais de ré-indexation complète (`graphify .`) de ta propre initiative ; incrémental seulement
  (hook git post-commit + `graphify update .` au sprint-end).

## Garde-fous
- Un seul objectif par sprint. Ne prétends jamais qu'un test a tourné sans l'avoir exécuté.
- Commit/push/déploiement/migration destructive : uniquement sur demande explicite.
- `PROGRESS.md` = état vivant court ; archive longue ailleurs.
<!-- CLAUDE-KIT:END -->"""
txt = p.read_text() if p.exists() else "# Règles projet\n\n"
if "<!-- CLAUDE-KIT:START" in txt:
    txt = re.sub(r"<!-- CLAUDE-KIT:START.*?<!-- CLAUDE-KIT:END -->", block, txt, flags=re.S)
else:
    txt = txt.rstrip() + "\n\n" + block + "\n"
p.write_text(txt)
print("CLAUDE.md : bloc workflow à jour")
PY

# --- 5. PROGRESS.md : seed seulement si absent ------------------------------
if [ ! -f PROGRESS.md ]; then
cat > PROGRESS.md <<'EOF'
# État du projet

## Objectif du dernier sprint
- (à définir)

## Réalisations terminées
-

## Fichiers impactés
-

## Décisions clés
-

## Validations effectuées
-

## Risques / points ouverts
-

## Prochaine étape exacte
- Définir la première tâche.
EOF
  echo "PROGRESS.md : créé (modèle)"
else
  echo "PROGRESS.md : conservé (existant)"
fi

echo "✅ Kit Claude Code installé (sauvegardes dans $BK)."
