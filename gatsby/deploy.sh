#!/bin/bash
# LongLife deploy: git push + SSH build on faion-net
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

echo "Pushing to GitHub..."
git push origin main 2>/dev/null || git push origin master 2>/dev/null || true

echo "Deploying to faion-net..."
source ~/bin/op_unlock.sh 2>/dev/null || true

SSH_CMD="cd ~/longlife-faion-net && \
  git checkout -- . && git clean -fd && git pull && \
  cd gatsby && npm ci --prefer-offline && npx gatsby build && \
  sudo rsync -a --delete public/ /var/www/longlife.faion.net/"

bash ~/bin/ssh-faion-net.sh "$SSH_CMD"

echo "Deployed: https://longlife.faion.net/"
