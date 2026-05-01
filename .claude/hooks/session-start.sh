#!/bin/bash
# Auto-injects plans/STATE.md and flags any plans/ file newer than STATE.md
# (likely a leftover from a prior session that ended abruptly).
set -e
PROJ="${CLAUDE_PROJECT_DIR:-$(pwd)}"
STATE="$PROJ/plans/STATE.md"

# Mark turn-start so the first turn's Stop hook has a baseline.
date +%s > "$PROJ/.claude/.turn-start"

if [ -f "$STATE" ]; then
  STATE_CONTENT=$(cat "$STATE")
else
  STATE_CONTENT="(no plans/STATE.md yet — fresh project; create it when planning begins.)"
fi

# Detect drift: any plans/ markdown newer than STATE.md = unfinished checkpoint.
STALE_LIST=""
if [ -f "$STATE" ]; then
  STALE_LIST=$(find "$PROJ/plans" -type f -name "*.md" -newer "$STATE" 2>/dev/null | sed "s|$PROJ/||g" | head -10)
fi

CONTEXT="Active planning state (auto-injected from plans/STATE.md):

$STATE_CONTENT"

if [ -n "$STALE_LIST" ]; then
  CONTEXT="$CONTEXT

⚠️  These plans/ files are newer than STATE.md — likely an unfinished checkpoint from a prior session that ended abruptly. Reconcile early in this session by syncing STATE.md to reflect what's in those files:
$STALE_LIST"
fi

jq -n --arg c "$CONTEXT" '{
  hookSpecificOutput: {
    hookEventName: "SessionStart",
    additionalContext: $c
  }
}'
