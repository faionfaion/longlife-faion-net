#!/bin/bash
set -euo pipefail

# Deploy longlife.media
#
# Generation and publishing live on different machines:
#
#   nero-prod  runs `generate` — writes articles and covers, commits, and pushes.
#   faion-net  serves the site and runs `publish`, `digest` and `site`.
#
# So "deploy" means two different things depending on where it runs:
#
#   on the web host      build the site in place and rsync it into the webroot
#   anywhere else        push the commits and stop; the web host builds on its own cron
#
# The second case used to SSH into faion-net and run `git reset --hard origin/main` there.
# That is why it no longer does: the publish ledger under state/tg_published is tracked,
# and resetting it to whatever the other machine last pushed would re-send articles the
# channel has already had. A machine that does not serve the site has no business
# rewriting the tree of one that does.
#
# (Before May 2026 the script always took the SSH path. After the pipeline moved onto
# faion-net that meant SSHing from the host to itself with no key authorised for the
# loop-back, so every nightly deploy failed and the site sat frozen on its April build for
# over three months.)

WEBROOT="/var/www/longlife.media"
SITE="longlife.media"
BRANCH="master"

cd "$(dirname "$0")/.."
ROOT="$PWD"

echo "==> Deploying $SITE"

if [ ! -d "$WEBROOT" ] && [ "$(hostname)" != "faion-net-new" ]; then
    echo "  Not the web host — pushing commits, the site builds where it is served."
    git push origin "HEAD:$BRANCH"
    echo "==> Pushed."
    exit 0
fi

echo "  Building in place."
cd "$ROOT/gatsby"
npm ci --silent 2>/dev/null || npm install --silent

npx gatsby clean
npx gatsby build

echo "  Publishing to $WEBROOT..."
sudo mkdir -p "$WEBROOT"
sudo rsync -a --delete "$ROOT/gatsby/public/" "$WEBROOT/"

sudo nginx -t && sudo systemctl reload nginx

echo "==> Deployed https://$SITE/"
