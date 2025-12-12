import logging
import time
from wechatpy.utils import check_signature
from wechatpy.exceptions import InvalidSignatureException
from wechatpy import parse_message, create_reply
from wechatpy.replies import TextReply
from wechatpy.crypto import WeChatCrypto
from wechat_publisher.config import WECHAT_TOKEN, WECHAT_AES_KEY, WECHAT_APPID
from wechat_publisher.llm_client import llm_client
import httpx
from wechat_publisher.token_manager import token_manager
import asyncio

logger = logging.getLogger(__name__)

def get_crypto():
    """Lazy init crypto"""
    if WECHAT_AES_KEY:
        return WeChatCrypto(WECHAT_TOKEN, WECHAT_AES_KEY, WECHAT_APPID)
    return None

def verify_wechat_signature(signature, timestamp, nonce, msg_signature=None):
    """
    If msg_signature is provided (Safe Mode), verify it against crypto.
    Otherwise verify standard signature.
    """
    try:
        if msg_signature:
             crypto = get_crypto()
             if crypto:
                 # In Safe Mode URL Check, echostr is encrypted? 
                 # Wait, for GET /verification, standard signature is used even in safe mode usually?
                 # No, in Safe Mode, GET request has signature, timestamp, nonce, echostr.
                 # The signature is still sha1(token, timestamp, nonce).
                 # BUT echostr might need decryption if using safe mode? 
                 # Let's check: 
                 # "Check Signature" logic is same. But echostr returned needs to be plain?
                 pass 
        
        # Standard Check (Always valid for Token validation)
        check_signature(WECHAT_TOKEN, signature, timestamp, nonce)
        return True
    except InvalidSignatureException:
        return False

def parse_wechat_message(xml_data, timestamp=None, nonce=None, msg_signature=None):
    """
    Supports both Plaintext and Safe Mode (Encrypted).
    """
    try:
        crypto = get_crypto()
        if crypto and msg_signature:
            decrypted_xml = crypto.decrypt_message(xml_data, msg_signature, timestamp, nonce)
            msg = parse_message(decrypted_xml)
        else:
            msg = parse_message(xml_data)
        return msg
    except Exception as e:
        logger.error(f"Parse Error: {e}")
        return None

async def process_user_message_background(openid: str, content: str):
    """
    1. Call LLM to get response.
    2. Send "Customer Service Message" (Custom Message) to user.
    """
    logger.info(f"Processing message from {openid}: {content}")
    
    try:
        # 1. Get LLM Response
        ai_response = await llm_client.get_chat_response(content)
        
        # 2. Send Custom Message
        await send_custom_message(openid, ai_response)
        
    except Exception as e:
        logger.error(f"Background Process Error: {e}")
        # Optionally send error message to user
        try:
            await send_custom_message(openid, "抱歉，由于系统繁忙，暂时无法回复。请稍后再试。")
        except:
            pass

async def send_custom_message(openid: str, content: str):
    """
    Sends a message to the user using the Customer Service API.
    POST https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token=ACCESS_TOKEN
    """
    access_token = token_manager.get_token()
    if not access_token:
        logger.error("Failed to get access token for sending custom message.")
        return

    url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={access_token}"
    
    payload = {
        "touser": openid,
        "msgtype": "text",
        "text": {
            "content": content
        }
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10)
        resp_json = response.json()
        if resp_json.get("errcode") != 0:
            logger.error(f"WeChat Custom Message API Error: {resp_json}")
        else:
            logger.info(f"Sent reply to {openid}")
    except Exception as e:
        logger.error(f"Failed to send custom message: {e}")
