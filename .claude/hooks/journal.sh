#!/usr/bin/env bash
# Hook SessionStart de Claude Code : donne le journal de sessions à Claude.
# Au démarrage d'une session (startup), Claude doit en faire le résumé.
# Après /clear, une reprise (resume) ou un résumé automatique de la conversation
# (compact), le journal n'est donné qu'en contexte : pas de nouveau résumé.
# Claude envoie sur l'entrée standard un JSON dont le champ "source" dit le cas.

f="${CLAUDE_PROJECT_DIR:-.}/.claude/SESSION_LOG.md"
[ -f "$f" ] || exit 0

source=$(sed -n 's/.*"source"[[:space:]]*:[[:space:]]*"\([a-z]*\)".*/\1/p' | head -n1)
if [ "$source" = startup ]; then
  echo "=== Journal de sessions (.claude/SESSION_LOG.md) : faire un résumé à l'utilisateur ==="
else
  echo "=== Journal de sessions (.claude/SESSION_LOG.md) : pour contexte, ne pas refaire de résumé ==="
fi
cat "$f"
