import sys
import os
import requests
import json
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from wechat_publisher.token_manager import token_manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("permission_test")

def check_material_batchget_permission():
    logger.info("--- Testing 'Material BatchGet' Permission (material/batchget_material type='news') ---")
    token = token_manager.get_token()
    url = f"https://api.weixin.qq.com/cgi-bin/material/batchget_material?access_token={token}"
    
    payload = {
        "type": "news", # Graphic Messages (Articles)
        "offset": 0,
        "count": 1
    }
    
    try:
        resp = requests.post(url, json=payload)
        data = resp.json()
        logger.info(f"Response: {data}")
        
        if data.get("errcode") is None or data.get("errcode") == 0:
            if "item" in data:
                logger.info("✅ material_batchget: GRANTED (Found items)")
                return True
            else:
                logger.info("✅ material_batchget: GRANTED (Empty list)")
                return True
        else:
            logger.error(f"❌ material_batchget: FAILED ({data.get('errcode')}: {data.get('errmsg')})")
            return False
            
    except Exception as e:
        logger.error(f"Exception: {e}")
        return False

if __name__ == "__main__":
    can_material = check_material_batchget_permission()
    
    summary = "\n--- SUMMARY ---\n"
    summary += f"Material Sync (material/batchget type='news'): {'✅ OK' if can_material else '❌ FAIL'}\n"
    print(summary)
