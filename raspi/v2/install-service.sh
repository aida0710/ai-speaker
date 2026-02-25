#!/bin/bash
# install-service.sh — systemd サービスファイルをインストール・更新する

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SERVICE_FILE="ai-speaker.service"
SYSTEMD_DIR="/etc/systemd/system"

echo "=== AI Speaker サービスをインストール ==="
echo "サービスファイル: $SCRIPT_DIR/$SERVICE_FILE"
echo "インストール先: $SYSTEMD_DIR/$SERVICE_FILE"
echo ""

# サービスファイルをコピー
sudo cp "$SCRIPT_DIR/$SERVICE_FILE" "$SYSTEMD_DIR/"
echo "✓ サービスファイルをコピーしました"

# systemd をリロード
sudo systemctl daemon-reload
echo "✓ systemd をリロードしました"

# サービスを有効化（起動時に自動起動）
sudo systemctl enable ai-speaker
echo "✓ サービスを有効化しました（起動時に自動起動）"

# サービスを再起動
sudo systemctl restart ai-speaker
echo "✓ サービスを再起動しました"

echo ""
echo "=== インストール完了 ==="
echo ""
echo "ステータス確認:"
sudo systemctl status ai-speaker --no-pager
echo ""
echo "ログ確認（リアルタイム）:"
echo "  journalctl -u ai-speaker -f"

