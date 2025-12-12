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


## 3. Interactive Bot (Chat)

The service now includes an **Interactive Chat Bot** handling standard WeChat text messages.

### Logic Flow
1.  **Webhook**: Receives POST request from WeChat at `/wechat/callback`.
2.  **Synchronous Reply**: to bypass "Unauthorized API (48001)" errors on unverified accounts, the bot uses **passive synchronous replies**.
    - It must generate and return the XML response within **5 seconds**.
    - Uses `google/gemini-2.5-flash-lite` (via OpenRouter) for speed.

### Features
- **Auto-Reply**: Chats with users using the configured LLM.
- **Safe Mode**: Supports WeChat's encryption/decryption (AES).

---

## 4. Configuration

### Environment Variables (`.env`)

#### WeChat Credentials
- `APPID`: WeChat App ID
- `SECRET`: WeChat App Secret
- `WECHAT_TOKEN`: Token for server verification
- `WECHAT_AES_KEY`: EncodingAESKey for message encryption

#### OpenRouter / LLM
- `OPENROUTER_API_KEY`: API Key
- `TEXT_MODEL`: Default model (e.g., `google/gemini-2.5-flash`)
- `TEXT_MODEL_LITE`: Fast model for chat (e.g., `google/gemini-2.5-flash-lite`)
- `TEXT_MODEL_PRO`: Powerful model (e.g., `google/gemini-3-pro-preview`)

#### Service Config
- `ADMIN_API_KEY`: Key for securing the Publish API.
- `REDIS_URL`: (Optional) For token caching.

---

## 5. Development & Deployment Guide

### A. One-Click Deployment (Recommended)
We provide a script `deployment.sh` that handles sync, build, and restart.

```bash
# From local project root
./deployment.sh
```

### B. Manual Deployment Credentials
Ensure you have the SSH key (`animagent.pem`) to access the server.
```bash
ssh -i /Users/lgg/coding/credentials/animagent.pem ubuntu@animagent.ai
```

### C. Manual Update Procedure
If you cannot use the script:

1.  **Sync Code to Server**:
    Use `rsync` to upload changed files.
    ```bash
    rsync -avz -e "ssh -i /Users/lgg/coding/credentials/animagent.pem" \
        /Users/lgg/coding/wechat/wechat-public-account/ \
        ubuntu@animagent.ai:/home/ubuntu/animagent-frontend/wechat-public-account/ \
        --exclude 'test*.py' \
        --exclude '__pycache__' \
        --exclude '.git'
    ```

2.  **Rebuild & Restart Service (On Server)**:
    SSH into the server and run (ensure you are in the correct directory matching `docker-compose.yml`):
    ```bash
    ssh -i "/Users/lgg/coding/credentials/animagent.pem" ubuntu@animagent.ai 'docker restart wechat-publisher'
    ```

3.  **Logs**:
    ```bash
    docker logs -f wechat-publisher
    ```
