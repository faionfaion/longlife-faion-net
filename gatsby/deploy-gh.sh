#!/bin/bash
set -euo pipefail

# Deploy longlife.faion.net from GitHub.
#
# 1. SSHs into faion-net
# 2. Pulls latest from github.com/faionfaion/longlife-faion-net
# 3. Builds Gatsby site on remote server
# 4. Copies to nginx webroot
# 5. Reloads nginx
#
# Prerequisites:
#   source ~/bin/op_unlock.sh

REPO_URL="https://github.com/faionfaion/longlife-faion-net.git"
BRANCH="main"
REMOTE_DIR="/home/faion/longlife-faion-net"
WEBROOT="/var/www/longlife.faion.net"

echo "==> Deploying longlife.faion.net (GitHub)"

# 1. Unlock 1Password if not already
if ! command -v op &>/dev/null || ! op whoami &>/dev/null 2>&1; then
    echo "  Unlocking 1Password..."
    source ~/bin/op_unlock.sh
fi

# 2. Get SSH credentials
HOST=$(op item get "SSH faion-net" --vault="Faion Personal" --fields host --reveal 2>/dev/null)
PORT=$(op item get "SSH faion-net" --vault="Faion Personal" --fields port --reveal 2>/dev/null)
USER=$(op item get "SSH faion-net" --vault="Faion Personal" --fields user --reveal 2>/dev/null)
KEY=$(op item get "SSH faion-net" --vault="Faion Personal" --fields ssh_private_key 2>/dev/null | tr -d '"')

KEYFILE=$(mktemp)
trap "rm -f $KEYFILE" EXIT
printf '%s\n' "$KEY" > "$KEYFILE"
chmod 600 "$KEYFILE"

SSH_CMD="ssh -i $KEYFILE -p $PORT -o StrictHostKeyChecking=no"

# 3. Clone or pull on remote server, build, deploy
$SSH_CMD "$USER@$HOST" bash -s -- "$REPO_URL" "$BRANCH" "$REMOTE_DIR" "$WEBROOT" <<'REMOTE_SCRIPT'
set -euo pipefail

REPO_URL="$1"
BRANCH="$2"
REMOTE_DIR="$3"
WEBROOT="$4"

echo "  [remote] Syncing repo..."
if [ -d "$REMOTE_DIR/.git" ]; then
    cd "$REMOTE_DIR"
    git fetch origin "$BRANCH" --quiet
    git reset --hard "origin/$BRANCH" --quiet
else
    git clone --branch "$BRANCH" --single-branch "$REPO_URL" "$REMOTE_DIR" --quiet
    cd "$REMOTE_DIR"
fi
echo "  [remote] At commit $(git rev-parse --short HEAD)"

# Build Gatsby
echo "  [remote] Installing dependencies..."
cd "$REMOTE_DIR/gatsby"
npm ci --silent 2>/dev/null || npm install --silent

echo "  [remote] Building Gatsby site..."
npx gatsby clean
npx gatsby build

# Deploy to webroot
echo "  [remote] Deploying to $WEBROOT..."
sudo mkdir -p "$WEBROOT"
sudo rsync -a --delete "$REMOTE_DIR/gatsby/public/" "$WEBROOT/"

# Update nginx config
if [ -f "$REMOTE_DIR/site/nginx/longlife.faion.net.conf" ]; then
    sudo cp "$REMOTE_DIR/site/nginx/longlife.faion.net.conf" /etc/nginx/sites-available/longlife.faion.net
    sudo ln -sf /etc/nginx/sites-available/longlife.faion.net /etc/nginx/sites-enabled/longlife.faion.net
fi

sudo nginx -t && sudo systemctl reload nginx

echo "  [remote] Done."
REMOTE_SCRIPT

echo "==> Deployed to https://longlife.faion.net/ (GitHub)"
