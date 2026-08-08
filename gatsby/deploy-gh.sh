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

# Purge the Cloudflare cache after a deploy. Without this the freshly built pages sit
# behind stale CDN copies: article URLs are new so they resolve, but the homepage, the tag
# lists, the sitemap and rss keep serving the previous build, so a new post is invisible on
# the front page until the TTL expires. Creds live outside the repo in /srv/longlife.
purge_cdn() {
    local env="/srv/longlife/cloudflare.env"
    [ -f "$env" ] || { echo "  (no cloudflare.env; skipping CDN purge)"; return 0; }
    # shellcheck disable=SC1090
    . "$env"
    echo "  Purging Cloudflare cache..."
    curl -s -X POST \
        -H "X-Auth-Email: $CF_EMAIL" -H "X-Auth-Key: $CF_API_KEY" \
        -H "Content-Type: application/json" \
        --data '{"purge_everything":true}' \
        "https://api.cloudflare.com/client/v4/zones/$CF_ZONE/purge_cache" >/dev/null \
        && echo "  Cache purged." || echo "  CDN purge failed (non-fatal)."
}

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

# Gatsby 5 intermittently dies with a "query result" race on this many pages; a clean
# rebuild clears it. Retry once so a transient flake does not leave the nightly deploy
# reporting success while the site stays on yesterday's build.
build() { npx gatsby clean && npx gatsby build; }
build || { echo "  build failed, retrying once after clean..."; build; }

# The build must have produced a homepage, or there is nothing safe to publish. Bail
# rather than rsync --delete an empty/partial public over the live site.
if [ ! -s "$ROOT/gatsby/public/index.html" ]; then
    echo "  ERROR: build produced no index.html, refusing to publish" >&2
    exit 1
fi

echo "  Publishing to $WEBROOT..."
sudo mkdir -p "$WEBROOT"
sudo rsync -a --delete "$ROOT/gatsby/public/" "$WEBROOT/"

sudo nginx -t && sudo systemctl reload nginx
purge_cdn

echo "==> Deployed https://$SITE/"
