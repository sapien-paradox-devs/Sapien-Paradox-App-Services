#!/bin/bash
# Per-turn checkpoint nudge.
# If this turn modified any plans/ file but plans/STATE.md was not updated,
# soft-block to prompt the model to consider whether STATE.md needs syncing.
PROJ="${CLAUDE_PROJECT_DIR:-$(pwd)}"
TS="$PROJ/.claude/.turn-start"
STATE="$PROJ/plans/STATE.md"

# No turn marker → first run or crash recovery. Skip silently.
[ ! -f "$TS" ] && exit 0

# Did any plans/ markdown file get touched this turn?
TOUCHED=$(find "$PROJ/plans" -type f -name "*.md" -newer "$TS" 2>/dev/null | wc -l | tr -d ' ')

# Was STATE.md touched this turn?
STATE_FRESH=0
if [ -f "$STATE" ] && [ "$STATE" -nt "$TS" ]; then
  STATE_FRESH=1
fi

# Drift detected → soft block.
if [ "$TOUCHED" -gt 0 ] && [ "$STATE_FRESH" -eq 0 ]; then
  REASON="Checkpoint nudge: this turn modified plans/ files but plans/STATE.md was not. Decide before stopping:
- If a cross-cutting decision was locked, focus shifted, or a new open question surfaced → update plans/STATE.md (Locked decisions / Open questions / Active focus / Next action / Recent thread).
- If only a component spec was refined without affecting cross-cutting state → reply briefly acknowledging no STATE.md update is needed and stop.

Sessions can end abruptly. Do not accumulate decisions across turns — write them as they land."

  jq -n --arg r "$REASON" '{decision: "block", reason: $r}'
  exit 0
fi

exit 0
