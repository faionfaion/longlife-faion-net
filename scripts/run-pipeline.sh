#!/bin/bash
# LongLife pipeline runner — called by cron on both machines.
#
# The work is split across two hosts, because covers are rendered through the Codex CLI
# and Codex is only installed and authenticated on nero-prod:
#
#   nero-prod (UTC)          faion-net (UTC)
#   3 3 * * *  generate      5 9,12,15,18 * * *  publish
#                            43 20 * * *         digest
#                            30 5 * * *          site
#
# nero-prod writes articles and covers, commits and pushes. faion-net pulls, sends to
# Telegram and rebuilds the site. Only faion-net ever touches the channel or the webroot,
# which is what keeps the two hosts from posting over each other.

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

# Activate a venv if one is present. faion-net shares ~/.venv-media across its media
# pipelines; nero-prod keeps a per-project .venv because generate needs the Claude Agent
# SDK. Fall through to system python3 on a host with neither.
if [ -f "$PROJECT_DIR/.venv/bin/activate" ] && [ -z "${VIRTUAL_ENV:-}" ]; then
    # shellcheck disable=SC1091
    source "$PROJECT_DIR/.venv/bin/activate"
elif [ -f "$HOME/.venv-media/bin/activate" ] && [ -z "${VIRTUAL_ENV:-}" ]; then
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
    # --autostash: state/logs and state/plans are tracked and rewritten every run, so the
    # tree is essentially never clean at sync time and a plain rebase would refuse to start.
    git rebase --autostash origin/master || git rebase --abort
    git push origin HEAD:master || echo "push failed — prod is still ahead of origin"
} >> "$LOG_DIR/cron.log" 2>&1 || true

echo "$(date '+%Y-%m-%d %H:%M:%S') Pipeline $MODE started" >> "$LOG_DIR/cron.log"

# `site` is not a pipeline mode — it is the web host rebuilding from whatever the sync
# above just pulled down. Generation happens on the other machine now, so without this the
# articles it writes would never reach the site.
if [ "$MODE" = "site" ]; then
    bash "$PROJECT_DIR/gatsby/deploy-gh.sh" >> "$LOG_DIR/cron.log" 2>&1
    EXIT_CODE=$?
else
    python3 -m pipeline "$MODE" -v >> "$LOG_DIR/cron.log" 2>&1
    EXIT_CODE=$?

    # Push what the run produced. The sync at the top only pushes what was already
    # committed when the run started, which on a generate run is nothing that matters.
    if [ "$MODE" = "generate" ]; then
        git push origin HEAD:master >> "$LOG_DIR/cron.log" 2>&1 \
            || echo "$(date '+%Y-%m-%d %H:%M:%S') push failed — articles are local only" \
               >> "$LOG_DIR/cron.log"
    fi
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') Pipeline $MODE exit: $EXIT_CODE" >> "$LOG_DIR/cron.log"
echo "---" >> "$LOG_DIR/cron.log"
