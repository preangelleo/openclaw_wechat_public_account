import sys
import os
import requests
import json
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from wechat_publisher.token_manager import token_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("send_test_card")

def send_test_card(openid: str):
    logger.info(f"Sending Article Card (msgtype='news') to {openid}...")
    token = token_manager.get_token()
    url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={token}"
    
    # Payload for a "Link Card" (Article style but links to URL)
    payload = {
        "touser": openid,
        "msgtype": "news",
        "news": {
            "articles": [
                {
                    "title": "测试文章卡片 - Link Card",
                    "description": "这是一条测试消息，用于验证后台能否给你发送图文链接卡片。\n如果看到这就说明成功了！",
                    "url": "https://animagent.ai",
                    "picurl": "https://mmbiz.qpic.cn/mmbiz_jpg/GkFqKvoZz64uQzQxQ2nXXqXyQzQxQ2nXXqXyQzQx/0?wx_fmt=jpeg" # Placeholder, ideally use a real one or upload one
                }
            ]
        }
    }
    
    resp = requests.post(url, json=payload)
    data = resp.json()
    
    if data.get("errcode") == 0:
        logger.info("✅ SUCCESS: Sent 'news' card.")
    else:
        logger.error(f"❌ FAILED: {data}")
        # If 48001, we cannot send active custom messages.
        # But wait, user asked "if we can send article card".
        # If this fails, we must rely on "Passive Reply" (XML) when user messages us.
        
if __name__ == "__main__":
    target_openid = "o6yGojp55mYQe5cM8ZthkjwtmSY4"
    send_test_card(target_openid)
