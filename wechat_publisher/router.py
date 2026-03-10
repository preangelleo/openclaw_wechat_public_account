from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Query, Response
from wechatpy.utils import check_signature
from wechatpy.exceptions import InvalidSignatureException
from wechatpy import parse_message
from wechatpy.crypto import WeChatCrypto
import logging
import logging
import os
from .bot_handler import process_user_message_background
from .sync_service import sync_service
from .msg_logger import log_message
from wechatpy.replies import TextReply, ArticlesReply

from .memory_manager import memory_manager
from .llm_client import llm_client

logger = logging.getLogger("wechat_bot")
router = APIRouter()

@router.get("/wechat/callback")
async def wechat_verification(
    signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...),
    wx_token: str = Query(None, description="WeChat Token")
):
    """
    WeChat Server Verification (GET).
    """
    wx_token = wx_token or os.getenv("WECHAT_TOKEN")
    if not wx_token:
        raise HTTPException(status_code=400, detail="Missing credentials in query and .env")

    try:
        check_signature(wx_token, signature, timestamp, nonce)
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
    msg_signature: str = Query(None), # Required for Safe Mode
    wx_token: str = Query(None),
    wx_aes_key: str = Query(None),
    wx_appid: str = Query(None),
    wx_secret: str = Query(None), # needed if background reply is used
    openrouter_api_key: str = Query(None),
    openrouter_text_model: str = Query(None),
    bot_persona: str = Query(None),
    welcome_message: str = Query(None),
    db_url: str = Query(None)
):
    """
    WeChat Message Receiver (POST).
    """
    # 0. Environment Variable Fallback
    wx_token = wx_token or os.getenv("WECHAT_TOKEN")
    wx_aes_key = wx_aes_key or os.getenv("WECHAT_AES_KEY")
    wx_appid = wx_appid or os.getenv("APPID")
    wx_secret = wx_secret or os.getenv("SECRET")
    openrouter_api_key = openrouter_api_key or os.getenv("OPENROUTER_API_KEY")
    bot_persona = bot_persona or os.getenv("BOT_PERSONA")
    welcome_message = welcome_message or os.getenv("WELCOME_MESSAGE")

    if not wx_token or not wx_appid:
        logger.error("Missing required webhook credentials from query string and .env")
        raise HTTPException(status_code=400, detail="Missing credentials")

    # 1. Read XML Body
    body = await request.body()
    
    # 2. Verify & Decrypt (Support Safe Mode)
    crypto = None
    if wx_aes_key:
        crypto = WeChatCrypto(wx_token, wx_aes_key, wx_appid)
    
    try:
        if msg_signature and crypto:
            decrypted_xml = crypto.decrypt_message(body, msg_signature, timestamp, nonce)
        else:
            check_signature(wx_token, signature, timestamp, nonce)
            decrypted_xml = body
            
        # 3. Parse Message
        msg = parse_message(decrypted_xml)
        

        # 4. Handle Text Messages
        if msg.type == 'text':
            content = msg.content.strip()
            # LOGGING (MO)
            log_message(msg.source, content, msg_type='text', direction='MO')
            
            
            # --- FEATURE: Article Search & Card Reply ---
            # --- UNIFIED NLU FLOW ---
            
            # 1. Retrieve Context
            openid = msg.source
            if db_url:
                memory_manager.db_url = db_url # Assumes memory_manager uses db_url
            history = memory_manager.get_context(openid) if hasattr(memory_manager, 'get_context') else []
            
            # 2. Get AI Decision & Response (JSON)
            nlu_result = await llm_client.get_chat_response(msg.content, history=history, openrouter_api_key=openrouter_api_key, openrouter_text_model=openrouter_text_model, bot_persona=bot_persona)
            
            # 3. Update Memory (User)
            memory_manager.update_context(openid, msg.content, 'user')
            
            # 4. Process Decision
            reply_xml = None
            
            if nlu_result.get("needs_search"):
                keyword = nlu_result.get("search_keywords")
                logger.info(f"NLU Decision: SEARCH '{keyword}'")
                
                if keyword:
                    # --- AUTO SYNC (User Request) ---
                    # Ensure DB is fresh with latest 5 articles before searching
                    try:
                        if db_url:
                            # Need appid, secret to sync
                            sync_service.sync_recent_articles(wx_appid, wx_secret, limit=5, db_url=db_url)
                    except Exception as e:
                        logger.error(f"Auto-sync failed: {e}")
                        
                    articles = sync_service.search_articles(keyword, db_url=db_url) if db_url else []
                    if articles:
                        # --- CASE A: Search Success ---
                        if len(articles) > 1:
                            # Multiple results: Use Text List (WeChat Limit Bypass)
                            logger.info(f"Found {len(articles)} articles. Using Text List to bypass 1-card limit.")
                            content_lines = [f"🔍 找到 {len(articles)} 篇关于 '{keyword}' 的文章："]
                            for i, art in enumerate(articles):
                                content_lines.append(f"\n{i+1}. <a href='{art['url']}'>{art['title']}</a>")
                            
                            reply_text = "".join(content_lines)
                            reply = TextReply(message=msg, content=reply_text)
                            
                            log_message(msg.source, reply_text, msg_type='text', direction='MT')
                            memory_manager.update_context(openid, reply_text, 'model')
                            reply_xml = reply.render()
                        else:
                            # Single result: Use Card (Visual is better)
                            logger.info("Found 1 article. Using Card Reply.")
                            reply = ArticlesReply(message=msg)
                            for art in articles:
                                # 1. Force HTTPS for images (WeChat requirement)
                                picurl = art['picurl']
                                if picurl and picurl.startswith("http://"):
                                    picurl = picurl.replace("http://", "https://")
                                    
                                reply.add_article({
                                    'title': art['title'],
                                    'description': art['description'],
                                    'image': picurl,
                                    'url': art['url']
                                })
                            
                            log_message(msg.source, "[Article Card Reply]", msg_type='news', direction='MT')
                            memory_manager.update_context(openid, f"[分享了文章: {articles[0]['title']}]", 'model')
                            reply_xml = reply.render()
                    else:
                        # --- CASE B: Search Empty -> TEXT FALLBACK ---
                        logger.info(f"Search empty for '{keyword}', falling back to text.")
                        # Force override LLM text because it might be "Searching..." or "Here is..." which is wrong if empty.
                        text_content = f"抱歉，未找到关于 '{keyword}' 的文章。"
                        
                        log_message(msg.source, text_content, msg_type='text', direction='MT')
                        memory_manager.update_context(openid, text_content, 'model')
                        
                        reply = TextReply(content=text_content, message=msg)
                        reply_xml = reply.render()
                else:
                    # Keyword somehow null
                    text_content = nlu_result.get("reply_content", "我无法理解您想搜索什么。")
                    log_message(msg.source, text_content, msg_type='text', direction='MT')
                    memory_manager.update_context(openid, text_content, 'model')
                    reply = TextReply(content=text_content, message=msg)
                    reply_xml = reply.render()
            else:
                 # --- CASE C: General Chat -> TEXT REPLY ---
                 logger.info(f"NLU Decision: CHAT")
                 text_content = nlu_result.get("reply_content", "收到。")
                 
                 log_message(msg.source, text_content, msg_type='text', direction='MT')
                 memory_manager.update_context(openid, text_content, 'model')
                 
                 reply = TextReply(content=text_content, message=msg)
                 reply_xml = reply.render()

            # 5. Encrypt & Return
            if msg_signature and crypto:
                encrypted_xml = crypto.encrypt_message(reply_xml, nonce, timestamp)
                return Response(content=encrypted_xml, media_type="application/xml")
            else:
                return Response(content=reply_xml, media_type="application/xml")
            
        # 5. Handle Subscribe Events (Optional)
        elif msg.type == 'event' and msg.event == 'subscribe':
             # Return a passive XML reply instantly for welcome message
             logger.info(f"New User Subscribed: {msg.source}")
             
             # Prioritize dynamically passed/env welcome message over welcome.md
             if welcome_message:
                 logger.info("Using dynamic welcome_message from query/.env")
                 welcome_content = welcome_message
             else:
                 # Read welcome message from welcome.md
                 try:
                     current_dir = os.path.dirname(os.path.abspath(__file__))
                     welcome_path = os.path.join(current_dir, "welcome.md")
                     
                     if os.path.exists(welcome_path):
                         with open(welcome_path, "r", encoding="utf-8") as f:
                             welcome_content = f.read()
                     else:
                         logger.warning(f"welcome.md not found at {welcome_path}")
                         welcome_content = """感谢您关注本公众号。如果你在使用中遇到任何问题，欢迎随时发送消息寻求帮助。"""
                 except Exception as e:
                     logger.error(f"Failed to read welcome.md: {e}")
                     welcome_content = """感谢您关注本公众号。如果你在使用中遇到任何问题，欢迎随时发送消息寻求帮助。"""

             log_message(msg.source, welcome_content, msg_type='text', direction='MT')
             
             reply = TextReply(content=welcome_content, message=msg)
             reply_xml = reply.render()
             
             if msg_signature and crypto:
                encrypted_xml = crypto.encrypt_message(reply_xml, nonce, timestamp)
                return Response(content=encrypted_xml, media_type="application/xml")
             else:
                return Response(content=reply_xml, media_type="application/xml")
             
    except InvalidSignatureException:
        logger.warning(f"Invalid Signature. Sig: {signature} TS: {timestamp}")
        raise HTTPException(status_code=403, detail="Invalid signature")
    except Exception as e:
        logger.error(f"Error processing message: {e}")

    # ALWAYS return "success" or empty string to tell WeChat we received it OK.
    return Response(content="success", media_type="text/plain")
