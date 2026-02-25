#!/bin/bash
# deploy.sh — git pull して ai-speaker サービスを再起動する

set -e

REPO_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
SERVICE=ai-speaker

echo "=== git pull ==="
git -C "$REPO_DIR" pull

echo "=== restart $SERVICE ==="
sudo systemctl restart "$SERVICE"
sudo systemctl status "$SERVICE" --no-pager
