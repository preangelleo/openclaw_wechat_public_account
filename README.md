# OpenClaw WeChat Publisher Service

The **OpenClaw WeChat Publisher** is a stateless, containerized microservice API built to automate publishing "image-text" articles (Drafts) and multimedia assets to WeChat Official Accounts. It supports dynamic credential injection, making it safe and easy to deploy as a multi-tenant or open-source service.

## 📚 General Documentation
*   **[Setup Guide (README-SETUP.md)](./README-SETUP.md)**: Instructions on how to configure your WeChat Official Account and obtain credentials.
*   **Internal Logic Flow**: Detailed state machine documents available in `process_logic.md`.

## 1. API Usage

### Endpoint
- **Method**: `POST`
- **Path**: `/publish` (e.g. `http://your-server:5006/publish`)

### Authentication
**Header Required** (Deployment Gateway Security):
`X-Admin-Api-Key: <your_admin_api_key>` 

*(Configured via `ADMIN_API_KEY` in your `.env` file on deployment).*

## 2. API Reference

The service exposes a **Unified Endpoint** `POST /publish` that handles different types of publishing based on the `publish_type` parameter. **Because the service is stateless, all business-logic credentials must be passed in the JSON payload.**

### Request Structure
```json
{
  "publish_type": "article" | "video" | "voice" | "image",
  "title": "Title String",
  "...": "(type-specific fields)",
  "credentials": {
    "wx_appid": "YOUR_WECHAT_APP_ID",
    "wx_secret": "YOUR_WECHAT_APP_SECRET",
    "openrouter_api_key": "YOUR_OPENROUTER_KEY",
    "db_url": "optional_postgres_url_for_syncing"
  }
}
```

---

### A. Publish Article (Draft)
Creates a new draft in a WeChat Official Account. Supports Markdown content with Tables, Lists, and Images. Optionally uses LLMs to structure the Markdown strictly for WeChat's DOM renderer.

**Payload**:
```json
{
  "publish_type": "article",
  "title": "Future of AI Agents",
  "author": "Animagent Team",
  "digest": "Summary of the article.",
  "cover_image_index": 1,
  "content_source_url": "https://example.com/blog",
  "use_llm_parser": true,
  "images_list": [
    {
      "image_index": 1,
      "image_type": "url",
      "image_url": "https://example.com/cover.jpg"
    }
  ],
  "article_markdown": "# Title\n\nContent with **Markdown**.\n\n![alt](image_1)",
  "credentials": {
    "wx_appid": "...",
    "wx_secret": "...",
    "openrouter_api_key": "..."
  }
}
```

---

### B. Upload Video (Permanent Material)
Uploads a video file to WeChat Permanent Material storage. **Limit**: MAX 20MB.

**Payload**:
```json
{
  "publish_type": "video",
  "title": "Video Title",
  "introduction": "Video Description",
  "media_source": {
    "image_type": "url", 
    "image_url": "https://example.com/video.mp4" 
  },
  "credentials": { ... }
}
```

---

### C. Upload Voice (Permanent Material)
Uploads an audio file (MP3/AMR) to WeChat. **Limit**: MAX 2MB, < 60 seconds recommended.

**Payload**:
```json
{
  "publish_type": "voice",
  "title": "Voice Title", 
  "media_source": {
    "image_type": "url",
    "image_url": "https://example.com/audio.mp3"
  },
  "credentials": { ... }
}
```

---

### D. Upload Image (Permanent Material)
Uploads an image to WeChat (e.g., for creating a gallery).

**Payload**:
```json
{
  "publish_type": "image",
  "media_source": {
     "image_type": "base64",
     "image_base64": "..."
  },
  "credentials": { ... }
}
```

---

## 3. Interactive Webhook Bot
The SDK contains a fully functional WeChat Webhook receiver located at `/wechat/callback`. 

To support stateless multi-tenant deployment, **all decryption keys must be provided as URL parameters** when configuring your Webhook inside the WeChat Admin Portal.

Example Webhook URL configuration:
`https://your-server.com/wechat/callback?wx_token=XXX&wx_aes_key=YYY&wx_appid=ZZZ&wx_secret=AAA`

*Note: For complete setup context, see [`README-SETUP.md`](./README-SETUP.md).*

---

## 4. Deployment

### Using Docker Compose
1. Copy `.env.example` to `.env` and set `ADMIN_API_KEY`.
2. Run Docker Compose:
```bash
docker-compose up -d --build
```
The service will start on port `5006` internally.

### Production Script
If deploying to the MacroAlpha infrastructure, simply use the deployment script:
```bash
./deploy.sh
```
This script ensures isolated environments and excludes local `.env` syncing to protect production deployments.
