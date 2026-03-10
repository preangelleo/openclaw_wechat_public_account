# Internal Migration Guide (Animagent / Idea2Presentation)

The `wechat-public-account` service has been refactored into the open-source, stateless `openclaw_wechat_public_account` service. 

**It no longer loads your WeChat credentials from `.env`.** 

If your internal services (like `animagent` tools or `idea2presentation` publishers) call this API, you must update your HTTP requests to include the `credentials` dictionary in the JSON payload.

## Updating API Calls (`POST /publish`)

### Old Payload Example
```json
{
  "publish_type": "article",
  "title": "My Article",
  "article_markdown": "..."
}
```

### New Payload Example
You MUST now wrap all requests with a `credentials` object. The `ADMIN_API_KEY` is still required in the HTTP Header `X-Admin-Api-Key`.

```json
{
  "publish_type": "article",
  "title": "My Article",
  "article_markdown": "...",
  "credentials": {
    "wx_appid": "wx1234567890abcdef",
    "wx_secret": "your_wechat_secret_here",
    "openrouter_api_key": "sk-or-v1-...",
    "db_url": "postgresql://animagent_admin:your_password@animagent-postgres:5432/animagent_backend_api"
  }
}
```

*Note: `openrouter_api_key` and `db_url` are optional depending on whether you are using LLM parsers or DB features, but `wx_appid` and `wx_secret` are strictly required.*

## Webhook Updates in WeChat Admin
If you previously configured the WeChat Official Account Webhook to point to `https://oc.macroalpha.io/endpoint/wechat-publisher/wechat/callback`, you must now:

1. Update the URL to point to the new project path (e.g., `/endpoint/openclaw_wechat_public_account/...`).
2. Inject the credentials directly into the URL query parameters so the stateless webhook can decrypt messages and reply:

```text
https://oc.macroalpha.io/endpoint/openclaw_wechat_public_account/wechat/callback?wx_token=YOUR_TOKEN&wx_aes_key=YOUR_AES_KEY&wx_appid=YOUR_APPID&openrouter_api_key=YOUR_OPENROUTER_KEY&wx_secret=YOUR_APPSECRET&db_url=YOUR_POSTGRES_URL
```

If you do not update the webhook URL, the interactive chat bot will fail to decrypt messages.
