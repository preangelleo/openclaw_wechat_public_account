import sys
import os
import requests
import json
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from wechat_publisher.token_manager import token_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("permission_test")

def check_sync_permission():
    logger.info("--- Testing 'Article Sync' Permission (freepublish/batchget) ---")
    token = token_manager.get_token()
    url = f"https://api.weixin.qq.com/cgi-bin/freepublish/batchget?access_token={token}"
    
    payload = {
        "offset": 0,
        "count": 1,
        "no_content": 1 # 1=Return check result only? No, just don't return content to save bandwidth if possible?
        # Actually API param is just offset/count.
    }
    
    try:
        resp = requests.post(url, json=payload)
        data = resp.json()
        logger.info(f"Response: {data}")
        
        if data.get("errcode") == 0 or "item" in data:
            logger.info("✅ sync_permission: GRANTED")
            return True
        else:
            logger.error(f"❌ sync_permission: FAILED ({data.get('errcode')}: {data.get('errmsg')})")
            return False
    except Exception as e:
        logger.error(f"Exception: {e}")
        return False

def check_custom_send_permission():
    logger.info("--- Testing 'Custom Send' Permission (message/custom/send) ---")
    token = token_manager.get_token()
    url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={token}"
    
    # Use a fake OpenID, we expect 40003 (invalid openid) if permission exists,
    # or 48001 (unauthorized) if permission is missing.
    fake_openid = "oPkvb6L8_FAKE_OPENID_123456"
    
    payload = {
        "touser": fake_openid,
        "msgtype": "text",
        "text": {"content": "Test"}
    }
    
    try:
        resp = requests.post(url, json=payload)
        data = resp.json()
        logger.info(f"Response: {data}")
        
        errcode = data.get("errcode")
        if errcode == 40003: # Invalid OpenID, but API call went through -> Permission OK
             logger.info("✅ custom_send_permission: LIKELY GRANTED (Got Invalid OpenID error as expected)")
             return True
        elif errcode == 48001:
             logger.error("❌ custom_send_permission: DENIED (48001 Unauthorized)")
             return False
        elif errcode == 0:
             logger.info("✅ custom_send_permission: GRANTED (Miraculously sent to fake ID?)")
             return True
        else:
             logger.warning(f"⚠️ custom_send_permission: UNCERTAIN ({errcode}: {data.get('errmsg')})")
             return False
    except Exception as e:
        logger.error(f"Exception: {e}")
        return False

if __name__ == "__main__":
    can_sync = check_sync_permission()
    can_send = check_custom_send_permission()
    
    summary = "\n--- SUMMARY ---\n"
    summary += f"Article Sync (freepublish): {'✅ OK' if can_sync else '❌ FAIL'}\n"
    summary += f"Active Card Reply (custom/send): {'✅ OK' if can_send else '❌ FAIL'}\n"
    print(summary)
