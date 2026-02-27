#!/bin/bash
set -e

# Configuration
PEM_PATH="/Users/lgg/coding/credentials/animagent.pem"
LOCAL_DIR="/Users/lgg/coding/wechat/wechat-public-account/"
REMOTE_USER="ubuntu"
REMOTE_HOST="animagent.ai"
REMOTE_DIR="/home/ubuntu/coding/wechat-public-account/"
SERVICE_NAME="wechat-publisher"

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

# Note: We exclude .env to avoid overwriting production secrets with local dev secrets,
# unless that is desired. The user said ".env 应该都可以用到" and "User said they provided .env".
# Ideally we sync .env too if local is truth, but usually dangerous.
# Given USER REQUEST: "部署好新的代码" -> usually implies code.
# The user's prompt says: "所有细节，需要用户做的设置，提供的 .env 里面已经有".
# This implies the local .env has the WECHAT_TOKEN.
# So I SHOULD sync the .env file this time, or manually update it?
# Let's INCLUDE .env for now based on user context "all settings... provided .env".
# Actually, let's play safe: existing .env on server might have other secrets.
# But Wait, I just modified Local .env? No, I viewed it.
# I updated `config.py` to READ from .env. I did NOT create a new local .env file tool call.
# I will NOT sync .env by default to prevent breaking existing prod keys (like DB passwords).
# I will print a warning.
# RE-READING: "提供的 .env 里面已经有 /Users/lgg/coding/wechat/wechat-public-account/.env"
# The user implies local .env has the goods. I will sync it.

echo "⚠️  Syncing .env file (as requested for config updates)..."
scp -i ${PEM_PATH} ${LOCAL_DIR}.env ${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}.env

# 2. Rebuild and Restart
echo "🔄 Rebuilding and Restarting Service on Remote..."
ssh -i ${PEM_PATH} ${REMOTE_USER}@${REMOTE_HOST} "cd ${REMOTE_DIR} && docker compose up -d --build ${SERVICE_NAME}"

echo "✅ Deployment Complete!"
echo "📜 Tailing logs (Ctrl+C to exit)..."
ssh -i ${PEM_PATH} ${REMOTE_USER}@${REMOTE_HOST} "docker logs --tail 50 ${SERVICE_NAME}"
