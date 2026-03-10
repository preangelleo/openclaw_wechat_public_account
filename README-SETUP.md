# WeChat Public Account Setup Guide

This guide explains how to configure your WeChat Official Account to work with the OpenClaw WeChat Publisher service.

## 1. Prerequisites
- A registered WeChat Official Account (Service Account or Subscription Account).
- The `openclaw_wechat_public_account` service deployed and running on a publicly accessible server (e.g., `https://your-domain.com/api/weixin-publish`).

## 2. Obtain Credentials from WeChat Admin Panel
1. Log in to the [WeChat Official Accounts Platform](https://mp.weixin.qq.com/).
2. Navigate to **Settings and Development (设置与开发)** -> **Basic Configuration (基本配置)**.
3. Note down your:
   - **AppID (开发者ID)**
   - **AppSecret (开发者密码)** - You may need to click "Reset" or "Enable" to view it. Make sure to whitelist your server's IP address.

## 3. Configure Server Webhook (Callback URL)
To allow the LLM to auto-reply to users and process events, you must configure the Server Configuration.

1. Under **Basic Configuration (基本配置)**, click **Enable (启用)** or **Modify Configuration (修改配置)** under **Server Configuration (服务器配置)**.
2. You will need to generate two secure random strings yourself:
   - **Token**: A string of 3-32 characters (e.g., `MySecureRandomToken123`).
   - **EncodingAESKey**: A 43-character alphanumeric string. You can click "Random Generate" on the WeChat page.
3. Fill in the **URL (服务器地址)**. 
   **CRITICAL STEP**: Because this service is stateless, you must pass all necessary credentials as URL query parameters in the Webhook URL:
   
   ```text
   https://your-domain.com/api/weixin-publish/wechat/callback?wx_token=<YOUR_TOKEN>&wx_aes_key=<YOUR_AES_KEY>&wx_appid=<YOUR_APPID>&openrouter_api_key=<YOUR_OPENROUTER_KEY>&wx_secret=<YOUR_APP_SECRET>
   ```
   *(Optional)*: If you deployed PostgreSQL and want chat memory/syncing, append `&db_url=<YOUR_POSTGRES_URL>`.

4. Fill in the **Token** field with the `<YOUR_TOKEN>` you chose.
5. Fill in the **EncodingAESKey** field with `<YOUR_AES_KEY>`.
6. Set **Message Encryption Method (消息加解密方式)** to **Safe Mode (安全模式)**.
7. Click **Submit**. WeChat will send a verification request to your server. If successful, it will be enabled.

## 4. Obtain OpenRouter API Key
If you want the bot to auto-reply using AI or parse Markdown heavily:
1. Go to [OpenRouter](https://openrouter.ai/).
2. Create an account and generate an API Key.
3. Use this key as `openrouter_api_key` in your payloads and Webhook URL.

## 5. Usage
Once configured, you can call the `/publish` endpoint on your server, passing these credentials in the JSON `credentials` block. See `README.md` for full API details!
