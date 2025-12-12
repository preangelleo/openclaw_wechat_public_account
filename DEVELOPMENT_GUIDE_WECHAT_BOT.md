# WeChat Official Account Code Assistant Development Guide

## Overview

This guide details how to implement an **Interactive AI Bot** for a WeChat Official Account.
**Goal**: Allow users to send private messages to the Official Account and receive AI-generated replies (powered by OpenRouter/Gemini).

**Current Architecture**:
- **Backend**: FastAPI
- **AI Service**: OpenRouter (Google Gemini 2.5 Flash)
- **Message Handling**: `wechatpy` (Cryptography/Parsing)
- **Reply Strategy**: Async/Background Task (to avoid 5s timeout limits)

---

## 1. Environment Configuration

Ensure your `.env` file contains the following critical credentials. 
**Note**: `WECHAT_TOKEN` and `WECHAT_AES_KEY` are configured in the WeChat Admin Console (Development -> Basic Configuration).

```bash
# WeChat Configuration
WECHAT_TOKEN=2A55fc83502E5dc5BaBDc3eaD90091b1
WECHAT_AES_KEY=sdwuvLMRSRuUyfEr7eftd5LIagPrWFIBKnq1xBHF3YO
WECHAT_APPID=wx... (Your App ID)
WECHAT_APP_SECRET=... (Your App Secret)

# AI Service Configuration
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_HEADER_SITE_URL=https://animagent.ai
OPENROUTER_HEADER_SITE_NAME=Animagent.ai

# Admin Security
ADMIN_API_KEY=ag_system_...

# Webhook URL (Must match WeChat Admin Config)
# Example: https://animagent.ai/api/weixin-publish/wechat/callback
```

---

## 2. Dependencies

Ensure `requirements.txt` includes:

```txt
fastapi
uvicorn
requests
wechatpy
cryptography
python-dotenv
redis (optional, for token caching)
```

---

## 3. Implementation Logic

### A. The missing piece: The Router
The previous implementation (`bot_handler.py`) provided logic but lacked the **FastAPI Router** to actually receive messages.

**Correct Implementation Pattern**:
1.  **GET Request**: WeChat Server Verification.
2.  **POST Request**: Receiving Messages.
3.  **Background Task**: Processing logic to avoid blocking the response.

### B. Core Code Structure

Create (or update) `wechat_publisher/router.py` (or integrate into `main.py`).

```python
from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Query, Response
from wechatpy.utils import check_signature
from wechatpy.exceptions import InvalidSignatureException
from wechatpy import parse_message
from wechatpy.crypto import WeChatCrypto
import logging
from .config import WECHAT_TOKEN, WECHAT_AES_KEY, WECHAT_APPID
from .bot_handler import process_user_message_background

logger = logging.getLogger("wechat_bot")
router = APIRouter()

@router.get("/wechat/callback")
async def wechat_verification(
    signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...)
):
    """
    WeChat Server Verification (GET).
    """
    try:
        check_signature(WECHAT_TOKEN, signature, timestamp, nonce)
        return int(echostr) # Must return integer/string directly
    except InvalidSignatureException:
        raise HTTPException(status_code=403, detail="Invalid signature")

@router.post("/wechat/callback")
async def wechat_message_handler(
    request: Request,
    background_tasks: BackgroundTasks,
    signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    msg_signature: str = Query(None) # Required for Safe Mode
):
    """
    WeChat Message Receiver (POST).
    """
    # 1. Read XML Body
    body = await request.body()
    
    # 2. Verify & Decrypt (Support Safe Mode)
    crypto = WeChatCrypto(WECHAT_TOKEN, WECHAT_AES_KEY, WECHAT_APPID)
    try:
        if msg_signature:
            decrypted_xml = crypto.decrypt_message(body, msg_signature, timestamp, nonce)
        else:
            check_signature(WECHAT_TOKEN, signature, timestamp, nonce)
            decrypted_xml = body
            
        # 3. Parse Message
        msg = parse_message(decrypted_xml)
        
        # 4. Handle Text Messages
        if msg.type == 'text':
            # Async Processing: Return strictly empty string or "success" to WeChat immediately
            # to prevent timeout (5s limit). Processing happens in background.
            background_tasks.add_task(
                process_user_message_background, 
                openid=msg.source, 
                content=msg.content
            )
            
        # 5. Handle Subscribe Events (Optional)
        elif msg.type == 'event' and msg.event == 'subscribe':
             # You can return a passive XML reply here instantly for welcome message
             pass
             
    except InvalidSignatureException:
        raise HTTPException(status_code=403, detail="Invalid signature")
    except Exception as e:
        logger.error(f"Error processing message: {e}")

    # ALWAYS return "success" or empty string to tell WeChat we received it OK.
    return Response(content="success", media_type="text/plain")
```

### C. Logic Handler (`bot_handler.py`)

The existing `bot_handler.py` handles the background processing well.

**Key Logic**:
1.  **Receive**: `process_user_message_background(openid, content)`
2.  **Think**: Call OpenRouter (`llm_client.get_chat_response`)
3.  **Reply**: Call WeChat Custom Message API (`/cgi-bin/message/custom/send`) because the synchronous response window (5s) has likely passed.

**Note**: To use the Custom Message API, your Official Account usually needs to be **Certified** (verified). If uncertified, you MUST reply within the 5s window using the Passive Response (XML return).

If you are **Uncertified**:
- You *cannot* use the async background method easily.
- You *must* optimize LLM speed and return the XML directly in the `wechat_message_handler` return value.

---

## 4. Deployment Steps

1.  **Update Code**: Add the router code to your project.
2.  **Register Router**: In `main.py`, add `app.include_router(wechat_router, prefix="/api/weixin-publish")`.
3.  **Deploy**: Restart the service.
4.  **Configure WeChat**:
    - Go to WeChat Admin -> Basic Configuration.
    - Set URL to `https://your-domain.com/api/weixin-publish/wechat/callback`.
    - Set Token and EncodingAESKey.
    - Click "Submit" (WeChat will hit your GET endpoint to verify).
    - Enable "Server Configuration".

---

## 5. Troubleshooting

-   **"Token Verification Failed"**: Check if `WECHAT_TOKEN` matches exactly. Ensure the GET endpoint returns the `echostr` as-is (clean response).
-   **"System Error" / No Reply**: Check server logs. If `gemini-2.5-flash` takes > 4.5s, the connection closes. Use the Background Task + Custom Message approach.

## 6. Official Implementation Rules (Crucial for Maintenance)

Based on WeChat Official Platform Documentation:

### A. The 5-Second Rule & "success" Reply
*   **Rule**: The WeChat server waits only **5 seconds** for a response.
*   **Consequence**: If your server takes longer (e.g., waiting for LLM), WeChat will:
    1.  Mark the request as failed.
    2.  Retry the request **3 times**, causing duplicate processing.
    3.  Eventually show the user "The Official Account cannot provide service".
*   **Solution (Implemented)**: 
    *   **Always** return `"success"` (or empty string) **immediately** upon receiving the POST request.
    *   Process the actual logic (LLM generation) in a **Background Task**.
    *   Send the actual reply via the **Customer Service Message API** (Custom Message) asynchronously.

### B. Access Token Management
*   **Rule**: Access Tokens expire after 2 hours (7200s).
*   **Best Practice**: Do not fetch a new token for every request (rate limits apply).
*   **Solution (Implemented)**:
    *   `TokenManager` caches the token locally (`access_token.json`) or in Redis.
    *   It automatically refreshes only when expired.
    *   **Maintenance**: If `access_token` errors occur frequently, check if another service is refreshing the token and verifying it, causing race conditions (Token Conflict).

### C. Security
*   **Signature Verification**: Every request from WeChat must be verified using `check_signature` with your `WECHAT_TOKEN`.
*   **Safe Mode**: If enabled in WeChat Admin, messages are encrypted. The current router supports `msg_signature` decryption.

---

## 7. Maintenance & Troubleshooting

### Updating Credentials
If you change the `Token` or `EncodingAESKey` in WeChat Admin:
1.  Update `.env` on the server:
    ```bash
    WECHAT_TOKEN=new_token
    WECHAT_AES_KEY=new_key
    ```
2.  Restart the service (`docker-compose restart wechat-publisher`).

### Debugging No-Reply Issues
1.  **Check Logs**: `docker logs -f wechat-public-account-wechat-publisher`
2.  **Verify Async Execution**: Ensure `process_user_message_background` is actually running.
3.  **Check WeChat Status**: If the bot replies "System Busy", it means the LLM failed or the Custom Message API failed.
4.  **IP Whitelist**: If logs show "Client IP not whitelisted", add the server IP to the WeChat Admin whitelist.
