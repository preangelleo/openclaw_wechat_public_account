import time
import requests
import redis
import logging
import json
import os

logger = logging.getLogger(__name__)

class TokenManager:
    """
    Manages WeChat Access Token with dual strategy:
    1. Local JSON file (access_token_{appid}.json) for persistence across restarts/local usage.
    2. Redis for distributed caching (if available).
    """
    def __init__(self):
        # We don't initialize redis here anymore; we'll do it per-request or lazily if we want to cache the client
        self.redis_clients = {}

    def _get_redis_client(self, redis_url: str):
        if not redis_url:
            return None
        if redis_url not in self.redis_clients:
            try:
                self.redis_clients[redis_url] = redis.from_url(redis_url)
            except Exception as e:
                logger.warning(f"Redis connection failed for {redis_url}: {e}")
                self.redis_clients[redis_url] = None
        return self.redis_clients[redis_url]

    def get_token(self, appid: str, secret: str, redis_url: str = None) -> str:
        """
        Retrieves valid access token. Checks File -> Redis -> API.
        """
        if not appid or not secret:
            raise ValueError("WeChat AppID and Secret are required to get a token.")
            
        token_key = f"wechat_access_token:{appid}"
        token_file = f"access_token_{appid}.json"
        
        # 1. Try Local File
        token = self._load_token_from_file(token_file)
        if token:
            return token

        # 2. Try Redis
        redis_client = self._get_redis_client(redis_url)
        if redis_client:
            try:
                token = redis_client.get(token_key)
                if token:
                    return token.decode("utf-8")
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")

        # 3. Fetch New
        return self.refresh_token(appid, secret, redis_url)

    def _load_token_from_file(self, token_file: str) -> str:
        if not os.path.exists(token_file):
            return None
            
        try:
            with open(token_file, 'r') as f:
                data = json.load(f)
                
            expires_at = data.get("expires_at", 0)
            if time.time() < expires_at:
                return data.get("access_token")
            else:
                logger.info(f"Local token file {token_file} expired.")
                return None
        except Exception as e:
            logger.warning(f"Failed to read token file: {e}")
            return None

    def _save_token_to_file(self, token_file: str, token: str, expires_in: int):
        buffer_seconds = 600 
        data = {
            "access_token": token,
            "expires_at": time.time() + expires_in - buffer_seconds 
        }
        try:
            with open(token_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning(f"Failed to save token file: {e}")

    def refresh_token(self, appid: str, secret: str, redis_url: str = None) -> str:
        url = "https://api.weixin.qq.com/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": appid,
            "secret": secret
        }
        
        logger.info(f"Refreshing WeChat Access Token from API for AppID: {appid}...")
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if "errcode" in data and data["errcode"] != 0:
                raise Exception(f"WeChat API Error: {data.get('errmsg')} (Code: {data.get('errcode')})")
                
            access_token = data["access_token"]
            expires_in = data["expires_in"]
            
            token_key = f"wechat_access_token:{appid}"
            token_file = f"access_token_{appid}.json"
            
            # Save to File
            self._save_token_to_file(token_file, access_token, expires_in)
            
            # Save to Redis
            redis_client = self._get_redis_client(redis_url)
            if redis_client:
                buffer_seconds = 600 # 10 minutes buffer
                try:
                    redis_client.setex(
                        token_key, 
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

