# WeChat Public Account SDK Deployment Guide

## 1. Environment Setup

The SDK requires the following environment variables in your `.env` file (`/home/ubuntu/wechat-public-account/.env`).

```ini
# WeChat Main Credentials
APPID=wxb20e40c1dec70823
SECRET=0dae304af8b936165af20f4e0021dabe

# API Security
ADMIN_API_KEY=ag_system_8a3758167e69...

# Content Generation
OPENROUTER_API_KEY=sk-or-v1-...
OPENROUTER_HEADER_SITE_URL=https://animagent.ai
OPENROUTER_HEADER_SITE_NAME=Animagent.ai

# Infrastructure
REDIS_URL=redis://animagent-redis:6379

# Gmail Service (For Email Preview Flow)
ANIMAGENT_GMAIL_ADDRESS=animagent.ai@gmail.com
ANIMAGENT_GMAIL_PASSWORD=gqkwepafxcjdaiqr

# Optional
WECHAT_ID=betashow
```

## 2. Deployment Steps

### Step 1: Sync Code to Server
```bash
rsync -avz --exclude '.git' --exclude '__pycache__' --exclude 'venv' --exclude '.env' \
    -e "ssh -i /Users/lgg/coding/credentials/animagent.pem" \
    /Users/lgg/coding/wechat/wechat-public-account ubuntu@animagent.ai:~/wechat/
```

### Step 2: Configure Environment
SSH into the server and ensure `.env` is configured.
```bash
ssh -i "/Users/lgg/coding/credentials/animagent.pem" ubuntu@animagent.ai
cd ~/wechat/wechat-public-account
# Ensure .env exists with required keys
docker compose up -d --build
```

### Step 3: Verify Deployment
```bash
docker logs -f wechat-publisher
# Check Health
curl http://localhost:5015/health
```

### Network Integration
Service uses `animagent-network` (external). Port: `5015`.

## 3. Maintenance

### Backup Strategy
We perform Manual Backups to `/home/ubuntu/wechat_backup/`.
**Command**:
```bash
mkdir -p /home/ubuntu/wechat_backup
# Backup Docker Image
docker save wechat-public-account_wechat-publisher | gzip > /home/ubuntu/wechat_backup/wechat_publisher_image_$(date +%Y%m%d).tar.gz
# Backup Source Code
tar -czf /home/ubuntu/wechat_backup/wechat_source_$(date +%Y%m%d).tar.gz -C /home/ubuntu/coding/ wechat-public-account
```

### Access Token Management
The system uses a **Dual-Layer Caching** strategy with a **Strict 110-minute Validity**:
- **Layer 1**: `access_token.json` (Local file for persistence).
- **Layer 2**: Redis (Distributed cache).
- **Validity**: Tokens expire in 7200s, but we refresh at **6600s** (110 mins) to provide a 10-minute safety buffer against network delays.

### Logs
To view realtime logs:
```bash
docker-compose logs -f --tail=100
```

## 4. API Usage

### Endpoint
- **Public**: `https://animagent.ai/api/weixin-publish/publish`
- **Internal**: `http://wechat-publisher:5015/publish`

### Authentication
Header: `X-Admin-Api-Key: <ADMIN_API_KEY>`

### Email Approval Flow (Recommended)
Add `preview_email` to your payload.
1. The API creates a Draft.
2. An email is sent to `preview_email`.
3. User clicks "Review" then "PUBLISH NOW".
4. The article is published via the `/approve` endpoint.

Refer to `README.md` for full payload examples.
Refer to `process_logic.md` for internal state machine details.
