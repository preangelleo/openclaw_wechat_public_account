# WeChat Public Account Publisher Service

A microservice to automate publishing "image-text" articles (Drafts) to a WeChat Official Account. It provides a RESTful API secured by an Admin API Key and supports deployment via Docker.

## 📚 Documentation
For a deep dive into the internal logic, state machines, and detailed workflows (including the "Email Approval" flow vs "Direct Publish"), please refer to [`process_logic.md`](./process_logic.md).

## 1. API Usage

### Endpoint
- **Internal (Docker Network)**: `http://wechat-publisher:5015/publish`
- **External (Public)**: `http://animagent.ai/api/weixin-publish` (Requires Reverse Proxy setup)
- **Method**: `POST`

### Authentication
**Header Required**:
`X-Admin-Api-Key: <your_admin_api_key>` 

(Value can be found in `.env` as `ADMIN_API_KEY`)

```

## 2. Integration Examples

### Python (via `requests`)

```python
import requests
import json

url = "http://animagent.ai/api/weixin-publish"
api_key = "ag_system_8a3758167e69..."

### Request Body (JSON)

```json
{
  "title": "Future of AI Agents",
  "author": "Animagent Team",
  "digest": "An in-depth look at how AI agents are transforming workflows.",
  "cover_image_index": 1,
  "content_source_url": "https://animagent.ai/blog/future-of-ai",
  "preview_email": "preangelleo@gmail.com",
  "auto_publish": false,
  "images_list": [
    {
      "image_index": 1,
      "image_type": "url",
      "image_url": "https://animagent.ai/assets/cover.jpg",
      "image_alt": "Article Cover"
    },
    {
      "image_index": 2,
      "image_type": "base64",
      "image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRg...", 
      "image_alt": "Architecture Diagram"
    },
    {
      "image_index": 3,
      "image_type": "url",
      "image_url": "https://animagent.ai/assets/chart.png",
      "image_alt": "Performance Chart"
    }
  ],
  "article_markdown": "# Future of AI Agents\n\nAI agents are evolving rapidly.\n\n## Architecture\n\nHere is how they work:\n\n![architecture](image_2)\n\n## Performance\n\n![chart](image_3)\n\nRead more at our official blog."
}
```

### Parameters Guide
- **`title`**: Article Title (Required).
- **`author`**: Author Name (Optional).
- **`digest`**: Short summary shown in the chat list (Optional).
- **`cover_image_index`**: Which image from `images_list` to use as the cover (Default: 1).
- **`content_source_url`**: "Read More" link at the bottom of the article (Optional).
- **`preview_email`**: Email address to receive the draft preview link and "Publish Now" button (Recommended).
- **`auto_publish`**: If `true`, publishes immediately without preview (Caution).
- **`images_list`**: List of images used in the article.
    - `image_index`: ID referenced in Markdown as `![alt](image_X)`.
    - `image_type`: `url` or `base64`.
    - `image_url` / `image_base64`: The source content.
- **`article_markdown`**: The article content in Markdown format. Use `image_index` to embed images.

### Response

**Success (200 OK)**
```json
{
  "errcode": 0,
  "errmsg": "ok",
  "media_id": "MEDIA_ID",
  "url": "URL_TO_PREVIEW_ARTICLE"
}
```

**Error (400 Bad Request / 500 Internal Server Error)**
```json
{
  "error": "Error message details"
}
```

```python
payload = {
    "title": "Future of AI Agents",
    "author": "Animagent Team",
    "digest": "An in-depth look at how AI agents are transforming workflows.",
    "cover_image_index": 1,
    "content_source_url": "https://animagent.ai/blog/future-of-ai",
    "preview_email": "preangelleo@gmail.com",
    "auto_publish": False,
    "images_list": [
        {
            "image_index": 1,
            "image_type": "url",
            "image_url": "https://animagent.ai/assets/cover.jpg",
            "image_alt": "Article Cover"
        },
        {
            "image_index": 2,
            "image_type": "base64",
            "image_base64": "data:image/jpeg;base64,/9j/4AAQSkZJRg...",
            "image_alt": "Architecture Diagram"
        },
        {
            "image_index": 3,
            "image_type": "url",
            "image_url": "https://animagent.ai/assets/chart.png",
            "image_alt": "Performance Chart"
        }
    ],
    "article_markdown": "# Future of AI Agents\n\nAI agents are evolving rapidly.\n\n## Architecture\n\nHere is how they work:\n\n![architecture](image_2)\n\n## Performance\n\n![chart](image_3)\n\nRead more at our official blog."
}

headers = {
    "X-Admin-Api-Key": api_key,
    "Content-Type": "application/json"
}

response = requests.post(url, json=payload, headers=headers)
print(response.json())
```

### Internal Docker Call

From another service in `animagent-network`:

```python
url = "http://wechat-publisher:5015/publish"
# ... headers and payload same as above
```

## 3. Configuration

- **Environment Variables** (`.env`):
  - `APPID`, `SECRET`: WeChat Credentials.
  - `ADMIN_API_KEY`: Key for securing this API.
  - `OPENROUTER_API_KEY`: For LLM content structuring.

- **Port**: Defaults to `5015`.

## 4. Development & Deployment Guide

This section is critical for future maintainers handling code updates and server maintenance.

### A. Repository Locations
- **Local (Dev Machine)**: `/Users/lgg/coding/wechat/wechat-public-account`
- **Production Server (Animagent.ai)**: `/home/ubuntu/coding/wechat-public-account`

### B. Prerequisite: Deployment Credentials
Ensure you have the SSH key (`animagent.pem`) to access the server.
```bash
ssh -i /path/to/animagent.pem ubuntu@animagent.ai
```

### C. Standard Update Procedure (Pushing Code Changes)
If you modify source code locally (e.g., `publisher.py` logic), follow these steps to deploy:

1.  **Sync Code to Server**:
    Use `rsync` to upload changed files (excluding temp files/caches).
    ```bash
    rsync -avz -e "ssh -i /Users/lgg/coding/credentials/animagent.pem" \
        /Users/lgg/coding/wechat/wechat-public-account/ \
        ubuntu@animagent.ai:/home/ubuntu/coding/wechat-public-account/ \
        --exclude 'test*.py' \
        --exclude '__pycache__' \
        --exclude 'access_token.json' \
        --exclude '.git'
    ```

2.  **Rebuild & Restart Service (On Server)**:
    SSH into the server and run the following commands to rebuild the Docker image and restart the container.
    ```bash
    # SSH into server
    ssh -i "/Users/lgg/coding/credentials/animagent.pem" ubuntu@animagent.ai

    # Go to project directory
    cd /home/ubuntu/coding/wechat-public-account

    # Rebuild and Restart (Zero downtime is not guaranteed, but it's fast)
    # --build: Forces image rebuild to pick up new code
    # -d: Detached mode
    docker-compose up -d --build --force-recreate
    ```

3.  **Clean Up (Optional but Recommended)**:
    Remove unused images to save disk space.
    ```bash
    docker image prune -f
    ```

### D. Server-Side Maintenance

#### 1. Check Logs
To see real-time logs of the service:
```bash
cd /home/ubuntu/coding/wechat-public-account
docker-compose logs -f --tail=100
```

#### 2. Restarting Nginx
If you change Nginx configs:
```bash
sudo systemctl reload nginx
```

#### 3. Access Token Maintenance
The service caches the WeChat Access Token in `access_token.json` (inside the container volume/path) and Redis.
If you need to force a token refresh, simple restart the container or wait for it to expire.

### E. Environment Variables
The `.env` file on the server is located at:
`/home/ubuntu/coding/wechat-public-account/.env`

If you add new variables locally, remember to:
1. Update `.env` locally.
2. `rsync` it to the server (or manually edit it on the server).
3. Restart the container (`docker-compose up -d`).

---

### F. Run Local Dev Server
```bash
# Install dependencies
pip install -r requirements.txt

# Run FastAPI
python main.py
```
Server runs at `http://0.0.0.0:5015`.
