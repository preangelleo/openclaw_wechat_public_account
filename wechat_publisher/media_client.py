import hashlib
import requests
import base64
import os
import logging
import io
import mimetypes
from PIL import Image
from typing import Dict, Optional, Union, List
from .token_manager import token_manager
from .config import REDIS_URL
import redis

logger = logging.getLogger(__name__)

class MediaClient:
    def __init__(self, redis_url=REDIS_URL):
        self.redis_client = redis.from_url(redis_url)
        self.url_map_key = "wechat_media_url_map" # Map hash -> wechat_url (for body images)
        self.media_id_map_key = "wechat_media_id_map" # Map hash -> media_id (for permanent materials)

    def _get_bytes_content(self, media_data: Dict) -> bytes:
        """
        Extracts bytes from the input dictionary (url or base64 or path).
        Supports 'type': 'url' | 'base64' | 'path'
        """
        src_type = media_data.get('type', 'base64') # default to base64 if not specified, legacy support
        # legacy check: if 'image_type' serves as type
        if 'image_type' in media_data:
            src_type = media_data['image_type']
            
        if src_type == 'base64':
            # Support both 'image_base64' and 'media_base64' keys
            b64_str = media_data.get('image_base64') or media_data.get('media_base64')
            if not b64_str:
                raise ValueError("Missing base64 data")
            if ',' in b64_str:
                b64_str = b64_str.split(',')[1]
            return base64.b64decode(b64_str)
            
        elif src_type == 'url':
            url = media_data.get('image_url') or media_data.get('media_url')
            if not url: raise ValueError("Missing URL")
            resp = requests.get(url, timeout=60)
            resp.raise_for_status()
            return resp.content
            
        elif src_type == 'path':
             path = media_data.get('media_path')
             if not path or not os.path.exists(path):
                 raise ValueError(f"File path not found: {path}")
             with open(path, 'rb') as f:
                 return f.read()
        else:
            raise ValueError(f"Unsupported media source type: {src_type}")

    def _calculate_hash(self, content: bytes) -> str:
        return hashlib.md5(content).hexdigest()

    def _compress_image(self, content: bytes, max_size_mb=2, quality=85) -> bytes:
        if len(content) <= max_size_mb * 1024 * 1024:
            return content
        image = Image.open(io.BytesIO(content))
        if image.mode in ("RGBA", "P"):
            image = image.convert("RGB")
        output = io.BytesIO()
        image.save(output, format="JPEG", quality=quality)
        return output.getvalue()

    def upload_image_for_article(self, image_data: Dict) -> str:
        """
        Uploads an image to be used INSIDE the article body.
        Returns the WeChat URL (http://mmbiz.qpic.cn/...).
        """
        content = self._get_bytes_content(image_data)
        content_hash = self._calculate_hash(content)
        
        cached_url = self.redis_client.hget(self.url_map_key, content_hash)
        if cached_url:
            return cached_url.decode('utf-8')

        content = self._compress_image(content)
        token = token_manager.get_token()
        url = f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={token}"
        files = {'media': ('image.jpg', content, 'image/jpeg')}
        
        resp = requests.post(url, files=files, timeout=60)
        data = resp.json()
        
        if "url" not in data:
             # Retry Logic for 40001 (Invalid Token)
             if data.get("errcode") == 40001:
                 logger.warning("AccessToken Expired (40001) in upload_image. Refreshing...")
                 token_manager.refresh_token()
                 token = token_manager.get_token()
                 url = f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={token}"
                 # Re-send request
                 # Note: 'files' dictates can be consumed? No, tuple ('name', bytes, mime) is reusable.
                 resp = requests.post(url, files={'media': ('image.jpg', content, 'image/jpeg')}, timeout=60)
                 data = resp.json()
                 if "url" in data:
                     wechat_url = data["url"]
                     self.redis_client.hset(self.url_map_key, content_hash, wechat_url)
                     return wechat_url

             raise Exception(f"Failed to upload image: {data}")
             
        wechat_url = data["url"]
        self.redis_client.hset(self.url_map_key, content_hash, wechat_url)
        return wechat_url

    def upload_permanent_material(self, media_data: Dict, material_type: str = "image", title: str = "", introduction: str = "") -> str:
        """
        General function to upload permanent materials (image, voice, video, thumb).
        Video requires title and introduction.
        """
        content = self._get_bytes_content(media_data)
        content_hash = self._calculate_hash(content)
        
        # Determine Cache Prefix to separate Image/Video/Voice namespaces in same hash map?
        # Or just mix them. Hash is MD5 of content, so collision is unlikely unless content identic.
        # But wait, video needs extra fields (title/intro), if those change, hash of content is same but output different?
        # WeChat Permanent Video doesn't update metadata easily. We will cache by CONTENT hash only for now.
        
        cached_id = self.redis_client.hget(self.media_id_map_key, content_hash)
        if cached_id:
             logger.info(f"Material hit cache: {content_hash}")
             return cached_id.decode('utf-8')

        token = token_manager.get_token()
        url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type={material_type}"
        
        # Prepare Files
        filename = "media.bin"
        if material_type == "image" or material_type == "thumb":
             filename = "image.jpg"
             content = self._compress_image(content) # Compress images only
             mime = "image/jpeg"
        elif material_type == "voice":
             filename = "voice.mp3"
             mime = "audio/mpeg"
        elif material_type == "video":
             filename = "video.mp4"
             mime = "video/mp4"

        files = {'media': (filename, content, mime)}
        payload = {}
        
        if material_type == "video":
            import json
            description = {
                "title": title or "Video Title",
                "introduction": introduction or "Video Introduction"
            }
            # WeChat requires 'description' field as JSON string for video
            payload = {"description": json.dumps(description, ensure_ascii=False)}
            
            # Check Size Limit (20MB for Permanent Video via API)
            # Official doc says 10MB sometimes, but observed limit is around 20MB.
            # Error 45002 confirms size limit.
            if len(content) > 20 * 1024 * 1024:
                raise ValueError(f"Video file size ({len(content)/(1024*1024):.2f} MB) exceeds WeChat API limit (20MB). Please compress the video.")

        try:
            resp = requests.post(url, files=files, data=payload, timeout=300) # Longer timeout for video
            data = resp.json()

            if "media_id" in data:
                 media_id = data["media_id"]
                 self.redis_client.hset(self.media_id_map_key, content_hash, media_id)
                 return media_id
            
            # Error Handling: Check for validation errors
            errcode = data.get("errcode")
            if errcode == 40001:
                # Token Expired
                logger.warning(f"AccessToken Expired (40001). Refreshing...")
                token_manager.refresh_token()
                # Retry once
                token = token_manager.get_token()
                url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type={material_type}"
                resp = requests.post(url, files={'media': (filename, content, mime)}, data=payload, timeout=300)
                data = resp.json()
                if "media_id" in data:
                     self.redis_client.hset(self.media_id_map_key, content_hash, data["media_id"])
                     return data["media_id"]

            if errcode in [45001, 88000]: # Capacity full
                 logger.warning(f"Upload failed (Capacity). Attempting cleanup.")
                 self.cleanup_oldest_materials(5)
                 # Retry
                 resp = requests.post(url, files={'media': (filename, content, mime)}, data=payload, timeout=300)
                 data = resp.json()
                 if "media_id" in data:
                      self.redis_client.hset(self.media_id_map_key, content_hash, data["media_id"]) 
                      return data["media_id"]

            raise Exception(f"Failed to upload {material_type}: {data}")

        except Exception as e:
            raise e

    def get_material_count(self) -> int:
        token = token_manager.get_token()
        url = f"https://api.weixin.qq.com/cgi-bin/material/get_materialcount?access_token={token}"
        resp = requests.get(url, timeout=30)
        data = resp.json()
        if "image_count" not in data: return 0
        return data["image_count"] # Just image count for cleaning strategy

    def batch_get_materials(self, offset: int, count: int) -> List[str]:
        token = token_manager.get_token()
        url = f"https://api.weixin.qq.com/cgi-bin/material/batchget_material?access_token={token}"
        payload = {
            "type": "image",
            "offset": offset,
            "count": count
        }
        resp = requests.post(url, json=payload, timeout=30)
        data = resp.json()
        media_ids = []
        if "item" in data:
            for item in data["item"]:
                media_ids.append(item["media_id"])
        return media_ids

    def delete_material(self, media_id: str):
        token = token_manager.get_token()
        url = f"https://api.weixin.qq.com/cgi-bin/material/del_material?access_token={token}"
        payload = {"media_id": media_id}
        requests.post(url, json=payload, timeout=30)
        logger.info(f"Deleted material: {media_id}")

    def cleanup_oldest_materials(self, count_to_delete=5):
        total_count = self.get_material_count()
        if total_count == 0: return
        offset = max(0, total_count - count_to_delete - 1)
        media_ids = self.batch_get_materials(offset, count_to_delete + 5)
        for mid in media_ids[:count_to_delete]:
            self.delete_material(mid)

    def upload_temporary_material(self, media_data: Dict, material_type="image") -> str:
        content = self._get_bytes_content(media_data)
        if material_type == "image":
            content = self._compress_image(content)
            
        token = token_manager.get_token()
        url = f"https://api.weixin.qq.com/cgi-bin/media/upload?access_token={token}&type={material_type}"
        
        filename = "temp.bin"
        mime = "application/octet-stream"
        if material_type == "image": filename, mime = "temp.jpg", "image/jpeg"
        elif material_type == "voice": filename, mime = "temp.mp3", "audio/mpeg"
        elif material_type == "video": filename, mime = "temp.mp4", "video/mp4"

        files = {'media': (filename, content, mime)}
        resp = requests.post(url, files=files, timeout=60)
        data = resp.json()
        
        if "media_id" not in data:
            if data.get("errcode") == 40001:
                 logger.warning("AccessToken Expired (40001) in upload_temporary. Refreshing...")
                 token_manager.refresh_token()
                 token = token_manager.get_token()
                 url = f"https://api.weixin.qq.com/cgi-bin/media/upload?access_token={token}&type={material_type}"
                 resp = requests.post(url, files={'media': (filename, content, mime)}, timeout=60)
                 data = resp.json()
                 if "media_id" in data:
                     return data["media_id"]

            raise Exception(f"Failed to upload temporary material: {data}")
        return data["media_id"]

media_client = MediaClient()
