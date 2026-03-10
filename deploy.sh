#!/bin/bash
set -e

# Configuration
PEM_PATH="/Users/lgg/coding/credentials/animagent.pem"
LOCAL_DIR="/Users/lgg/coding/macroalpha_projects/openclaw_wechat_public_account/"
REMOTE_USER="ubuntu"
REMOTE_HOST="oc.macroalpha.io"
REMOTE_DIR="/home/ubuntu/coding/openclaw_wechat_public_account/"
SERVICE_NAME="openclaw-wechat"

echo "=========================================="
echo "🚀 Deploying WeChat Bot to ${REMOTE_HOST}..."
echo "=========================================="

# 1. Sync Code
echo "📦 Syncing code using rsync..."
rsync -avz -e "ssh -i ${PEM_PATH}" \
    ${LOCAL_DIR} \
    ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR} \
    --exclude '__pycache__' \
    --exclude '.git' \
    --exclude '.venv' \
    --exclude '.env' \
    --exclude '*.pyc'

# Strict rule: NEVER sync .env to remote server, protecting their prod secrets.

# 2. Rebuild and Restart
echo "🔄 Rebuilding and Restarting Service on Remote..."
ssh -i ${PEM_PATH} ${REMOTE_USER}@${REMOTE_HOST} "cd ${REMOTE_DIR} && docker compose up -d --build ${SERVICE_NAME}"

echo "✅ Deployment Complete!"
echo "📜 Tailing logs (Ctrl+C to exit)..."
ssh -i ${PEM_PATH} ${REMOTE_USER}@${REMOTE_HOST} "docker logs --tail 50 ${SERVICE_NAME}"
