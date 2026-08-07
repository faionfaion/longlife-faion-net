#!/bin/bash
set -euo pipefail

# Deploy longlife.faion.net
#
# Two paths, chosen by whether the webroot is on this machine:
#
#   local   — the pipeline already runs on faion-net, so build and rsync in place.
#             This is the live path.
#   remote  — push to GitHub, then SSH in and build there. Kept for running a deploy
#             from a workstation.
#
# The pipeline moved onto faion-net in May 2026 but this script kept SSHing to
# 46.225.58.119 — from faion-net to itself, with no key authorised for the loop-back.
# Every nightly deploy failed with "Permission denied (publickey)" and the site sat
# frozen at its April build for over three months while articles kept accumulating.
#
# The remote path also runs `git reset --hard origin/$BRANCH`, which on faion-net would
# throw away the content commits the pipeline makes locally and has never pushed. That is
# the other reason the local path must not fall through to it.

REPO_URL="git@github.com:faionfaion/longlife-faion-net.git"
BRANCH="main"
REMOTE_DIR="/home/faion/longlife-faion-net"
WEBROOT="/var/www/longlife.faion.net"
SITE="longlife.faion.net"
SSH="ssh faion@46.225.58.119 -p 22022"

cd "$(dirname "$0")/.."
ROOT="$PWD"

echo "==> Deploying $SITE"

build_and_publish() {
    local src="$1"

    echo "  Installing deps..."
    cd "$src/gatsby"
    npm ci --silent 2>/dev/null || npm install --silent

    echo "  Building..."
    npx gatsby clean
    npx gatsby build

    echo "  Publishing to $WEBROOT..."
    sudo mkdir -p "$WEBROOT"
    sudo rsync -a --delete "$src/gatsby/public/" "$WEBROOT/"

    sudo nginx -t && sudo systemctl reload nginx
}

if [ -d "$WEBROOT" ] || [ "$(hostname)" = "faion-net-new" ]; then
    echo "  Webroot is local — building in place, no SSH."
    build_and_publish "$ROOT"
    echo "==> Deployed https://$SITE/"
    exit 0
fi

echo "  Pushing to GitHub..."
git push origin "$BRANCH" 2>/dev/null || true

$SSH bash -s -- "$REPO_URL" "$BRANCH" "$REMOTE_DIR" "$WEBROOT" "$SITE" <<'REMOTE'
set -euo pipefail
REPO_URL="$1"; BRANCH="$2"; REMOTE_DIR="$3"; WEBROOT="$4"; SITE="$5"

echo "  [remote] Syncing repo..."
if [ -d "$REMOTE_DIR/.git" ]; then
    cd "$REMOTE_DIR"
    git remote set-url origin "$REPO_URL" 2>/dev/null || true
    git fetch origin "$BRANCH" --quiet
    git reset --hard "origin/$BRANCH" --quiet
else
    git clone --branch "$BRANCH" --single-branch "$REPO_URL" "$REMOTE_DIR" --quiet
    cd "$REMOTE_DIR"
fi
echo "  [remote] At $(git rev-parse --short HEAD)"

echo "  [remote] Installing deps..."
cd "$REMOTE_DIR/gatsby"
npm ci --silent 2>/dev/null || npm install --silent

echo "  [remote] Building..."
npx gatsby clean
npx gatsby build

echo "  [remote] Deploying to $WEBROOT..."
sudo mkdir -p "$WEBROOT"
sudo rsync -a --delete "$REMOTE_DIR/gatsby/public/" "$WEBROOT/"

sudo nginx -t && sudo systemctl reload nginx
echo "  [remote] Done."
REMOTE

echo "==> Deployed https://$SITE/"
