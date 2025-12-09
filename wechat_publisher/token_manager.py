import time
import requests
import redis
import logging
import json
import os
from .config import WECHAT_APPID, WECHAT_APP_SECRET, REDIS_URL

logger = logging.getLogger(__name__)

class TokenManager:
    """
    Manages WeChat Access Token with dual strategy:
    1. Local JSON file (access_token.json) for persistence across restarts/local usage.
    2. Redis for distributed caching (if available).
    """
    def __init__(self, redis_url=REDIS_URL, token_file="access_token.json"):
        self.redis_client = None
        if redis_url:
            try:
                self.redis_client = redis.from_url(redis_url)
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}. Falling back to file only.")
        
        self.token_key = f"wechat_access_token:{WECHAT_APPID}"
        self.token_file = token_file

    def get_token(self) -> str:
        """
        Retrieves valid access token. Checks File -> Redis -> API.
        """
        # 1. Try Local File
        token = self._load_token_from_file()
        if token:
            return token

        # 2. Try Redis
        if self.redis_client:
            try:
                token = self.redis_client.get(self.token_key)
                if token:
                    return token.decode("utf-8")
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")

        # 3. Fetch New
        return self.refresh_token()

    def _load_token_from_file(self) -> str:
        if not os.path.exists(self.token_file):
            return None
            
        try:
            with open(self.token_file, 'r') as f:
                data = json.load(f)
                
            expires_at = data.get("expires_at", 0)
            if time.time() < expires_at:
                return data.get("access_token")
            else:
                logger.info("Local token file expired.")
                return None
        except Exception as e:
            logger.warning(f"Failed to read token file: {e}")
            return None

    def _save_token_to_file(self, token: str, expires_in: int):
        # User requested 110 minutes validity (10 min buffer)
        # 120 min = 7200s. 110 min = 6600s. Buffer = 600s.
        buffer_seconds = 600 
        data = {
            "access_token": token,
            "expires_at": time.time() + expires_in - buffer_seconds 
        }
        try:
            with open(self.token_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning(f"Failed to save token file: {e}")

    def refresh_token(self) -> str:
        url = "https://api.weixin.qq.com/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": WECHAT_APPID,
            "secret": WECHAT_APP_SECRET
        }
        
        logger.info("Refreshing WeChat Access Token from API...")
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "errcode" in data and data["errcode"] != 0:
                raise Exception(f"WeChat API Error: {data.get('errmsg')} (Code: {data.get('errcode')})")
                
            access_token = data["access_token"]
            expires_in = data["expires_in"]
            
            # Save to File
            self._save_token_to_file(access_token, expires_in)
            
            # Save to Redis
            if self.redis_client:
                buffer_seconds = 600 # 10 minutes buffer
                try:
                    self.redis_client.setex(
                        self.token_key, 
                        max(expires_in - buffer_seconds, 60), 
                        access_token
                    )
                except Exception as e:
                    logger.warning(f"Redis set failed: {e}")
            
            return access_token
            
        except Exception as e:
            logger.error(f"Failed to refresh token: {e}")
            raise

# Global instance
token_manager = TokenManager()
