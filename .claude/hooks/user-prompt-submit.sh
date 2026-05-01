#!/bin/bash
# Mark the start of each turn so the Stop hook can compare what was touched THIS TURN.
PROJ="${CLAUDE_PROJECT_DIR:-$(pwd)}"
date +%s > "$PROJ/.claude/.turn-start"
exit 0
