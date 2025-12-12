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

from .memory_manager import memory_manager
from .llm_client import llm_client

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
            # --- UNIFIED NLU FLOW ---
            
            # 1. Retrieve Context
            openid = msg.source
            history = memory_manager.get_context(openid)
            
            # 2. Get AI Decision & Response (JSON)
            nlu_result = await llm_client.get_chat_response(msg.content, history=history)
            
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
                        sync_service.sync_recent_articles(limit=5)
                    except Exception as e:
                        logger.error(f"Auto-sync failed: {e}")
                        
                    articles = sync_service.search_articles(keyword)
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
            if msg_signature:
                encrypted_xml = crypto.encrypt_message(reply_xml, nonce, timestamp)
                return Response(content=encrypted_xml, media_type="application/xml")
            else:
                return Response(content=reply_xml, media_type="application/xml")
            
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
