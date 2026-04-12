#!/bin/bash
set -euo pipefail

# Deploy longlife.faion.net
# Push to GitHub → SSH to faion-net → pull + build + deploy

REPO_URL="git@github.com:faionfaion/longlife-faion-net.git"
BRANCH="main"
REMOTE_DIR="/home/faion/longlife-faion-net"
WEBROOT="/var/www/longlife.faion.net"
SITE="longlife.faion.net"
SSH="ssh faion@46.225.58.119 -p 22022"

cd "$(dirname "$0")/.."

echo "==> Deploying $SITE"

# 1. Push to GitHub
echo "  Pushing to GitHub..."
git push origin "$BRANCH" 2>/dev/null || true

# 2. Remote: pull, build, deploy
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
