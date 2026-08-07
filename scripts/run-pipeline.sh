#!/bin/bash
# LongLife pipeline runner — called by cron.
#
# Cron schedule (from AGENTS.md, UTC):
#   3 3 * * *          bash ~/workspace/projects/longlife-faion-net/scripts/run-pipeline.sh generate
#   5 9,12,15,18 * * * bash ~/workspace/projects/longlife-faion-net/scripts/run-pipeline.sh publish
#   5 20 * * *         bash ~/workspace/projects/longlife-faion-net/scripts/run-pipeline.sh digest

set -euo pipefail

MODE="${1:-generate}"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOCK="/tmp/longlife-${MODE}.lock"
LOG_DIR="$PROJECT_DIR/state/logs"

mkdir -p "$LOG_DIR"

# Prevent concurrent runs of same mode
if [ -f "$LOCK" ]; then
    PID=$(cat "$LOCK" 2>/dev/null || echo "")
    if kill -0 "$PID" 2>/dev/null; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') Pipeline $MODE already running (PID $PID)" >> "$LOG_DIR/cron.log"
        exit 0
    fi
    rm -f "$LOCK"
fi
echo $$ > "$LOCK"
trap "rm -f $LOCK" EXIT

cd "$PROJECT_DIR"

# Load environment. `set -a` auto-exports every var from .env so child
# processes (python pipeline) inherit them — .env uses plain KEY=value with
# no `export`, so a bare `source` would keep them shell-local (e.g. an empty
# TG_BOT_TOKEN, which silently breaks publishing).
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:$PATH"
export HOME="${HOME:-/home/nero}"
set -a
[ -f "$HOME/workspace/.env" ] && source "$HOME/workspace/.env"
set +a

# Activate shared media venv if present (faion-net runtime). On hosts without
# this venv (e.g. nero-prod), fall through to system python3.
if [ -f "$HOME/.venv-media/bin/activate" ] && [ -z "${VIRTUAL_ENV:-}" ]; then
    # shellcheck disable=SC1091
    source "$HOME/.venv-media/bin/activate"
fi

# Sync with GitHub, both directions.
#
# The pipeline commits every article locally and nothing ever pushed them, so prod drifted
# 138 commits ahead of origin. That made `git pull --ff-only` fail on every run — silently,
# behind `|| true` — and code changes pushed to GitHub never reached the machine actually
# running the pipeline. It also left the 400-odd articles existing on one disk only.
#
# Rebase puts local content commits on top of whatever came from GitHub; a conflict aborts
# and leaves the tree exactly as it was, so a bad merge can never take the night's run down.
{
    git fetch origin master
    git rebase origin/master || git rebase --abort
    git push origin HEAD:master || echo "push failed — prod is still ahead of origin"
} >> "$LOG_DIR/cron.log" 2>&1 || true

echo "$(date '+%Y-%m-%d %H:%M:%S') Pipeline $MODE started" >> "$LOG_DIR/cron.log"

python3 -m pipeline "$MODE" -v >> "$LOG_DIR/cron.log" 2>&1
EXIT_CODE=$?

echo "$(date '+%Y-%m-%d %H:%M:%S') Pipeline $MODE exit: $EXIT_CODE" >> "$LOG_DIR/cron.log"
echo "---" >> "$LOG_DIR/cron.log"
