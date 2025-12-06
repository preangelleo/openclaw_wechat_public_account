# WeChat Official Account Backend Configuration Guide

To enable your SDK to publish articles, you must configure the WeChat Official Account Admin Panel (mp.weixin.qq.com).

## 1. IP Whitelist (Critical)
**Issue**: This is the most common cause of `40164 invalid ip` or `48001 api unauthorized` errors during token refresh or API calls.

**Action**:
1. Login to [WeChat MP Admin](https://mp.weixin.qq.com).
2. Navigate to **Development (开发) > Basic Configuration (基本配置)**.
3. Find **IP Whitelist (IP白名单)** and click **Configure**.
4. Add the Public IP address of the machine running the SDK.
    - **Local Testing**: Visit [whatismyip.com](https://whatismyip.com) to find your local network's public IP.
    - **Animagent.ai Server**: SSH into the server and run `curl ifconfig.me` to get the static IP.

> [!IMPORTANT]
> The IP whitelist changes typically take **10-15 minutes** to take effect.

## 2. Server Configuration (Token/EncodingAESKey)
**Status**: **Optional** for *Publishing*, but Required for *Webhooks/Message Receiving*.
- If you only want to *publish* articles, you do **not** need to enable the "Server Configuration" (URL/Token verification) section.
- You **DO** need the **AppID** and **AppSecret** from this page.

## 3. Account Permission Checks (Error 48001)
If you encounter `48001 api unauthorized` even after whitelisting IP:
- **Reason**: Your account type may not support the specific API interface.
- **Draft API (`draft/add`)**:
    - **Supported**: Verified Service Accounts, Verified Subscription Accounts.
    - **Limited**: Unverified Personal Subscription Accounts *usually* have basic access, but some advanced formatting or "Permanent Material" uploads might be restricted.
    - **Check**: Go to **Settings (设置) > Interface Permissions (接口权限)**. Check if "Draft Management (草稿箱管理)" and "Material Management (素材管理)" are marked as "Authorized" (已获得).

## 4. Docker & Production Setup
When deploying to `animagent.ai`:
1. Ensure the container has outbound internet access (standard Docker NAT handles this).
2. Ensure the Host IP is in the WeChat IP Whitelist.
3. The `access_token.json` will be automatically created in the container's volume (if configured) or ephemeral filesystem to persist tokens between restarts if volumes are mapped.

## Summary Checklist
- [ ] Obtained AppID and AppSecret.
- [ ] Added **Public IP** to WeChat IP Whitelist.
- [ ] Checked **Interface Permissions** in WeChat Admin.
