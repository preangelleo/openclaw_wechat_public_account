# OpenClaw WeChat Publisher Service

The **OpenClaw WeChat Publisher** is a stateless, containerized microservice API built to automate publishing "image-text" articles (Drafts) and multimedia assets to WeChat Official Accounts. It supports dynamic credential injection, making it safe and easy to deploy as a multi-tenant or open-source service.

> **⚠️ CAUTION: Stateless Architecture**
> This service does **NOT** persistently store any WeChat AppIDs, AppSecrets, or LLM API keys on the server or in `.env` files (except the administrative Gateway Key). **All business logic credentials must be securely injected by the caller in the JSON payload of every request.** Do not log or expose these payloads in your calling applications.

---

## 📚 General Documentation
*   **[OpenClaw AI Integration Guide](./README-FOR-OPENCLAW.md)**: Instructions on how to configure WeChat Official Account credentials, webhooks, and utilize this service as an AI Agent.

---

## 1. Authentication & Endpoint

### Endpoint
- **Base URL**: `http://<your-server>:5006` (Internal) or `https://<your-domain>/endpoint/openclaw_wechat_public_account` (Public Gateway)
- **Method**: `POST`
- **Path**: `/publish`

### Authentication
All requests must include the following header to pass the deployment gateway security:
```http
X-Admin-Api-Key: <your_admin_api_key>
```
*(This is the `ADMIN_API_KEY` configured in the server's `.env` file.)*

---

## 2. API Payload Structure (Unified Endpoint)

The system uses a unified `/publish` endpoint. The `publish_type` attribute dictates the required media fields.

### Common Base Schema (Required for ALL requests)
```json
{
  "publish_type": "article | video | voice | image",
  "title": "Title of your content",
  "credentials": {
    "wx_appid": "REQUIRED: Your WeChat AppID",
    "wx_secret": "REQUIRED: Your WeChat AppSecret",
    "openrouter_api_key": "OPTIONAL: Required only if `use_llm_parser` is true",
    "db_url": "OPTIONAL: Postgres URL for syncing states if applicable"
  }
}
```

---

### A. Publish Article (Draft)
Creates a new draft in a WeChat Official Account. Supports Markdown content with Tables, Lists, and Images. Optionally uses LLMs to structure the Markdown strictly for WeChat's DOM renderer.

**Specific Payload**:
```json
{
  "publish_type": "article",
  "title": "Future of AI Agents",
  "author": "Animagent Team",
  "digest": "Summary of the article (appears in preview).",
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
    "openrouter_api_key": "YOUR_OPENROUTER_KEY" 
  }
}
```
*Note: If `use_llm_parser` is `true`, `openrouter_api_key` MUST be provided in credentials to format the Markdown safely for WeChat's restricted HTML framework.*

---

### B. Upload Video (Permanent Material)
Uploads a video file to WeChat Permanent Material storage.

> **⚠️ WeChat Limitations imposed by API:**
> - Max File Size: **20 MB**
> - Supported Formats: MP4
> - Aspect Ratio checks may apply depending on your account type.

**Specific Payload**:
```json
{
  "publish_type": "video",
  "title": "Video Title",
  "introduction": "Detailed description of the video content",
  "media_source": {
    "image_type": "url", 
    "image_url": "https://example.com/video.mp4" 
  },
  "credentials": { ... }
}
```

---

### C. Upload Voice (Permanent Material)
Uploads an audio file to WeChat.

> **⚠️ WeChat Limitations imposed by API:**
> - Max File Size: **2 MB**
> - Max Length: **60 seconds** (Recommended)
> - Supported Formats: MP3, WMA, WAV, AMR

**Specific Payload**:
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
Uploads an image to WeChat (e.g., for creating a gallery or using inside future articles without re-uploading).

> **⚠️ WeChat Limitations imposed by API:**
> - Max File Size: **10 MB** (often strictly enforced to 2MB for certain material endpoints; keep it optimized).
> - Supported Formats: BMP, PNG, JPEG, JPG, GIF

**Specific Payload**:
```json
{
  "publish_type": "image",
  "media_source": {
     "image_type": "base64",
     "image_base64": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
  },
  "credentials": { ... }
}
```

---

## 3. Response Formats

The API returns standard HTTP status codes.

**✅ Success (200 OK)**
```json
{
  "status": "success",
  "media_id": "MEDIA_ID_RETURNED_BY_WECHAT",
  "url": "http://mmbiz.qpic.cn/..." 
}
```
*(Note: `url` is usually only returned for Image uploads, whereas Drafts/Video/Voice return a `media_id`)*

**❌ Error (400 Bad Request / 500 Internal Server Error)**
```json
{
  "status": "error",
  "message": "Detailed error message (e.g., 'wx_appid missing', or 'WeChat API returned 40001 invalid credential')"
}
```

---

## 4. Code Examples

### Python (using `requests`)
```python
import requests

url = "https://oc.macroalpha.io/endpoint/openclaw_wechat_public_account/publish"
headers = {
    "X-Admin-Api-Key": "ag_system_8a375...",
    "Content-Type": "application/json"
}

payload = {
    "publish_type": "article",
    "title": "Automated WeChat Post",
    "article_markdown": "Hello from OpenClaw!",
    "credentials": {
        "wx_appid": "wx1234567890abcdef",
        "wx_secret": "secret1234567890abcdef",
    }
}

response = requests.post(url, json=payload, headers=headers)
print(response.json())
```

### cURL
```bash
curl -X POST https://oc.macroalpha.io/endpoint/openclaw_wechat_public_account/publish \
  -H "X-Admin-Api-Key: ag_system_8a375..." \
  -H "Content-Type: application/json" \
  -d '{
    "publish_type": "image",
    "media_source": {
      "image_type": "url",
      "image_url": "https://example.com/test.png"
    },
    "credentials": {
      "wx_appid": "wx1234567890abcdef",
      "wx_secret": "secret1234567890abcdef"
    }
  }'
```

---

## 5. Interactive Webhook Bot (Message Receiver)

The SDK contains a fully functional WeChat Webhook receiver located at `/wechat/callback`. This is used to automatically respond to users sending messages to your Official Account.

**⚠️ Stateless Configuration Requirement:**
Because the server does not store `.env` states for individual WeChat accounts, **all decryption keys must be injected as URL parameters** when configuring your Webhook Server inside the WeChat Official Account Admin Portal.

**Webhook URL Configuration Format:**
```text
https://your-domain.com/endpoint/openclaw_wechat_public_account/wechat/callback?wx_token=YOUR_TOKEN&wx_aes_key=YOUR_ENCODING_AES_KEY&wx_appid=YOUR_APPID&wx_secret=YOUR_APP_SECRET
```
*WeChat will issue a `GET` request to verify the server using parameters. The Python application natively parses these `query parameters` to execute the AES-CBC decryption for WeChat's proprietary XML wrapper.*

---

## 6. Deployment & Operational Integrity

### 🚀 Using Deployment Script (Recommended)
If deploying to the MacroAlpha infrastructure, use the provided script. This script deliberately excludes `.env` files to prevent developer API keys from overwriting the gateway keys on the remote server.
```bash
bash deploy.sh
```

### 🐳 Using Docker Compose (Local Dev)
1. Copy `.env.example` to `.env` and set `ADMIN_API_KEY`.
2. Run Docker Compose:
```bash
docker-compose up -d --build
```
The service will start internally on the port assigned (e.g., `5006`).

### 🛑 Best Practices & Cautions
1. **Access Token Idempotency**: The application dynamically fetches WeChat Access Tokens using your AppID and AppSecret. WeChat limits API calls to fetch access tokens (usually 2000/day). If you scale this container horizontally, consider passing a `db_url` in the credentials to allow the containers to share and cache the Access Token.
2. **Reverse Proxy Rules**: If using Apache or Nginx, ensure the `/publish` and `/wechat/callback` routes do not strip URL Query Parameters, as the `/wechat/callback` relies on them for decryption.
3. **Timeouts**: Uploading large videos (20MB) may take significant time. Ensure your load balancer/gateway timeout (e.g., Apache `ProxyTimeout`) is set sufficiently high (e.g., 60-120 seconds).
