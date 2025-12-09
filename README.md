# WeChat Public Account Publisher Service

A microservice to automate publishing "image-text" articles (Drafts) and multimedia assets to a WeChat Official Account. It provides a RESTful API secured by an Admin API Key and supports deployment via Docker.

## 📚 Documentation
For a deep dive into the internal logic, state machines, and detailed workflows (including the "Email Approval" flow vs "Direct Publish"), please refer to [`process_logic.md`](./process_logic.md).

## 1. API Usage

### Endpoint
- **External (Public)**: `https://animagent.ai/api/weixin-publish/publish`
- **Internal (Docker Network)**: `http://wechat-publisher:5015/publish`
- **Method**: `POST`

### Authentication
**Header Required**:
`X-Admin-Api-Key: <your_admin_api_key>` 

(Value can be found in `.env` as `ADMIN_API_KEY`)

## 2. API Reference

The service exposes a **Unified Endpoint** `POST /publish` that handles different types of publishing based on the `publish_type` parameter.

### Request Structure
```json
{
  "publish_type": "article" | "video" | "voice" | "image",
  "title": "Title String",
  ... (type-specific fields)
}
```

---

### A. Publish Article (Draft)
Creates a new draft in WeChat Official Account. Supports Markdown content with Tables, Lists, and Images.

**Payload**:
```json
{
  "publish_type": "article",
  "title": "Future of AI Agents",
  "author": "Animagent Team",
  "digest": "Summary of the article.",
  "cover_image_index": 1,
  "content_source_url": "https://animagent.ai/blog",
  "preview_email": "user@example.com",
  "use_llm_parser": true,
  "images_list": [
    {
      "image_index": 1,
      "image_description": "Cover Image",
      "image_type": "url",
      "image_url": "https://example.com/cover.jpg"
    }
  ],
  "article_markdown": "# Title\n\nContent with **Markdown**.\n\n![alt](image_1)"
}
```
> **Note**: `use_llm_parser: true` is recommended for best table/list rendering.

---

### B. Upload Video (Permanent)
Uploads a video file to WeChat Permanent Material storage.
**Limit**: MAX 20MB.

**Payload**:
```json
{
  "publish_type": "video",
  "title": "Video Title",
  "introduction": "Video Description",
  "media_source": {
    "image_type": "base64", 
    "image_base64": "data:video/mp4;base64,AAAA..." 
  }
}
```
*Note: `image_type` supports "url", "base64", or "path" (internal).*

---

### C. Upload Voice (Permanent)
Uploads an audio file (MP3/AMR) to WeChat Permanent Material storage.
**Limit**: MAX 2MB, < 60 seconds recommended.

**Payload**:
```json
{
  "publish_type": "voice",
  "title": "Voice Title", 
  "media_source": {
    "image_type": "url",
    "image_url": "https://example.com/audio.mp3"
  }
}
```

---

### D. Upload Image (Permanent)
Uploads an image to WeChat Permanent Material storage (e.g., for creating a gallery).

**Payload**:
```json
{
  "publish_type": "image",
  "media_source": {
     "image_type": "base64",
     "image_base64": "..."
  }
}
```

## 3. Integration Examples

### Python (via `requests`)

#### Publish Article
```python
import requests

url = "https://animagent.ai/api/weixin-publish/publish"
headers = {"X-Admin-Api-Key": "YOUR_API_KEY"}

payload = {
    "publish_type": "article",
    "title": "Test Article",
    "article_markdown": "# Hello\n\nChecking tables:\n\n| A | B |\n|---|---|\n| 1 | 2 |",
    "images_list": [{"image_index": 1, "image_type": "url", "image_url": "https://placehold.co/600x400.jpg"}],
    "cover_image_index": 1
}

resp = requests.post(url, json=payload, headers=headers)
print(resp.json())
```

#### Upload Video
```python
import base64

# Read video file
with open("video.mp4", "rb") as f:
    b64_data = base64.b64encode(f.read()).decode('utf-8')

payload = {
    "publish_type": "video",
    "title": "Demo Video",
    "introduction": "A short demo.",
    "media_source": {
        "image_type": "base64",
        "image_base64": b64_data
    }
}

resp = requests.post(url, json=payload, headers=headers)
print(resp.json()) 
# Returns: {"status": true, "media_id": "...", "type": "video"}
```

### Curl

**Check Health**:
```bash
curl https://animagent.ai/api/weixin-publish/health
```

**Upload Image (Base64)**:
```bash
curl -X POST https://animagent.ai/api/weixin-publish/publish \
-H "X-Admin-Api-Key: YOUR_KEY" \
-H "Content-Type: application/json" \
-d '{
    "publish_type": "image",
    "media_source": {
        "image_type": "url",
        "image_url": "https://example.com/image.jpg"
    }
}'
```

## 4. Configuration

- **Environment Variables** (`.env`):
  - `APPID`, `SECRET`: WeChat Credentials.
  - `ADMIN_API_KEY`: Key for securing this API.
  - `OPENROUTER_API_KEY`: For LLM content structuring.

- **Port**: Defaults to `5015`.

## 5. Development & Deployment Guide

### A. Deployment Credentials
Ensure you have the SSH key (`animagent.pem`) to access the server.
```bash
ssh -i /path/to/animagent.pem ubuntu@animagent.ai
```

### B. Standard Update Procedure (Pushing Code Changes)
If you modify source code locally (e.g., `publisher.py` logic), follow these steps to deploy:

1.  **Sync Code to Server**:
    Use `rsync` to upload changed files.
    ```bash
    rsync -avz -e "ssh -i /Users/lgg/coding/credentials/animagent.pem" \
        /Users/lgg/coding/wechat/wechat-public-account/ \
        ubuntu@animagent.ai:/home/ubuntu/coding/wechat-public-account/ \
        --exclude 'test*.py' \
        --exclude '__pycache__' \
        --exclude '.git'
    ```

2.  **Rebuild & Restart Service (On Server)**:
    SSH into the server and run:
    ```bash
    ssh -i "/Users/lgg/coding/credentials/animagent.pem" ubuntu@animagent.ai 'cd ~/wechat-public-account && docker compose up -d --build wechat-publisher'
    ```

3.  **Logs**:
    ```bash
    docker logs -f wechat-publisher
    ```
