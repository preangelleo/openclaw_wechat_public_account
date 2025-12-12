from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Query, Response
from wechatpy.utils import check_signature
from wechatpy.exceptions import InvalidSignatureException
from wechatpy import parse_message
from wechatpy.crypto import WeChatCrypto
import logging
from .config import WECHAT_TOKEN, WECHAT_AES_KEY, WECHAT_APPID
from .bot_handler import process_user_message_background
from .sync_service import sync_service
from .msg_logger import log_message
from wechatpy.replies import TextReply, ArticlesReply

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
    except Exception as e:
        logger.error(f"Verification Check Failed: {e}")
        raise HTTPException(status_code=500, detail="Verification Failed")

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
            content = msg.content.strip()
            # LOGGING (MO)
            log_message(msg.source, content, msg_type='text', direction='MO')
            
            # --- FEATURE: Article Search & Card Reply ---
            # Trigger: "文章 Keyword" or "search Keyword"
            if content.startswith("文章") or content.lower().startswith("search"):
                keyword = content.replace("文章", "").replace("search", "").strip()
                if keyword:
                    article = sync_service.search_article(keyword)
                    if article:
                        # Construct Article Card (NewsReply)
                        # WechaPy ArticlesReply takes a list of dicts/Article objects
                        # params: title, description, image, url
                        reply = ArticlesReply(message=msg)
                        reply.add_article({
                            'title': article['title'],
                            'description': article['description'],
                            'image': article['picurl'],
                            'url': article['url']
                        })
                        
                        # LOGGING (MT - Card)
                        log_message(msg.source, f"Card: {article['title']}", msg_type='news', direction='MT')
                        
                        xml = reply.render()
                        if msg_signature:
                             encrypted_xml = crypto.encrypt_message(xml, nonce, timestamp)
                             return Response(content=encrypted_xml, media_type="application/xml")
                        else:
                             return Response(content=xml, media_type="application/xml")
            # ---------------------------------------------

            # SYNCHRONOUS MODE (Required for Unverified Accounts)
            # We must return XML within 5 seconds.
            # Using OpenRouter Gemini Flash should be fast enough.
            from .llm_client import llm_client
            
            # 1. Get AI Response
            ai_reply = await llm_client.get_chat_response(msg.content)
            
            # 2. Construct XML Reply
            # TextReply is already imported but let's use the one we imported at top if possible, 
            # OR keep local import if preferred. Local import at line 71 was: from wechatpy.replies import TextReply
            # We added TextReply to top imports, so we can use it.
            
            # LOGGING (MT - Text)
            log_message(msg.source, ai_reply, msg_type='text', direction='MT')
            
            reply = TextReply(content=ai_reply, message=msg)
            xml = reply.render()
            
            if msg_signature:
                # Safe Mode: Encrypt the reply
                encrypted_xml = crypto.encrypt_message(xml, nonce, timestamp)
                return Response(content=encrypted_xml, media_type="application/xml")
            else:
                return Response(content=xml, media_type="application/xml")
            
        # 5. Handle Subscribe Events (Optional)
        elif msg.type == 'event' and msg.event == 'subscribe':
             # You can return a passive XML reply here instantly for welcome message
             # For now, just return success
             pass
             
    except InvalidSignatureException:
        logger.warning(f"Invalid Signature. Sig: {signature} TS: {timestamp}")
        raise HTTPException(status_code=403, detail="Invalid signature")
    except Exception as e:
        logger.error(f"Error processing message: {e}")

    # ALWAYS return "success" or empty string to tell WeChat we received it OK.
    return Response(content="success", media_type="text/plain")
