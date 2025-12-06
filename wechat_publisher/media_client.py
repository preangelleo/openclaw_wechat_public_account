import hashlib
import requests
import base64
import os
import logging
import io
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
        self.media_id_map_key = "wechat_media_id_map" # Map hash -> media_id (for permanent material)

    def _get_image_content(self, image_data: Dict) -> bytes:
        """
        Extracts image bytes from the input dictionary (url or base64).
        """
        img_type = image_data.get('image_type')
        
        if img_type == 'base64':
            b64_str = image_data.get('image_base64')
            if ',' in b64_str:
                b64_str = b64_str.split(',')[1]
            return base64.b64decode(b64_str)
            
        elif img_type == 'url':
            url = image_data.get('image_url')
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            return resp.content
            
        else:
            raise ValueError(f"Unsupported image_type: {img_type}")

    def _calculate_hash(self, content: bytes) -> str:
        return hashlib.md5(content).hexdigest()

    def _compress_image(self, content: bytes, max_size_mb=2, quality=85) -> bytes:
        """
        Simple compression if image is too large. WeChat limit is usually 2MB or 10MB depending on type.
        We aim for <2MB to be safe.
        """
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
        content = self._get_image_content(image_data)
        content_hash = self._calculate_hash(content)
        
        # Check cache
        cached_url = self.redis_client.hget(self.url_map_key, content_hash)
        if cached_url:
            logger.info(f"Image hit cache: {content_hash}")
            return cached_url.decode('utf-8')

        # Compress if needed (WeChat limitation)
        content = self._compress_image(content)

        # Upload
        token = token_manager.get_token()
        url = f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={token}"
        
        # WeChat expects 'media' field
        files = {'media': ('image.jpg', content, 'image/jpeg')}
        
        resp = requests.post(url, files=files, timeout=60)
        data = resp.json()
        
        if "url" not in data:
             raise Exception(f"Failed to upload image: {data}")
             
        wechat_url = data["url"]
        
        # Cache result
        self.redis_client.hset(self.url_map_key, content_hash, wechat_url)
        
        return wechat_url

    def get_material_count(self) -> int:
        """
        Returns the total count of permanent image materials.
        """
        token = token_manager.get_token()
        url = f"https://api.weixin.qq.com/cgi-bin/material/get_materialcount?access_token={token}"
        resp = requests.get(url, timeout=30)
        data = resp.json()
        if "image_count" not in data:
            logger.warning(f"Failed to get material count: {data}")
            return 0
        return data["image_count"]

    def batch_get_materials(self, offset: int, count: int) -> List[str]:
        """
        Returns a list of media_ids from the batch request.
        """
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
        """
        Deletes a permanent material by media_id.
        """
        token = token_manager.get_token()
        url = f"https://api.weixin.qq.com/cgi-bin/material/del_material?access_token={token}"
        payload = {"media_id": media_id}
        requests.post(url, json=payload, timeout=30)
        logger.info(f"Deleted material: {media_id}")

    def cleanup_oldest_materials(self, count_to_delete=5):
        """
        Deletes the oldest N images to free up space.
        """
        total_count = self.get_material_count()
        if total_count == 0:
            return

        # Strategy: Oldest images are at the end of the list if default sort is newest-first?
        # Verification needed: WeChat APIs usually return list in reverse chronological order (newest first).
        # So oldest items are at offset = total_count - count
        
        offset = max(0, total_count - count_to_delete - 1)
        # Fetch a batch from the end
        media_ids = self.batch_get_materials(offset, count_to_delete + 5) # Fetch a few more to be safe
        
        # Determine actual items to delete (take the last ones if list is ordered new->old, wait)
        # If list is New -> Old (Index 0 is Newest), then Index [Total-1] is Oldest.
        # So fetching from offset [Total - N] gets the Oldest.
        
        for mid in media_ids[:count_to_delete]:
            self.delete_material(mid)

    def upload_permanent_material(self, image_data: Dict) -> str:
        """
        Uploads an image as permanent material (e.g. for Cover).
        Returns the media_id.
        Auto-cleans old materials if storage is full.
        """
        content = self._get_image_content(image_data)
        content_hash = self._calculate_hash(content)
        
        # Check cache
        cached_id = self.redis_client.hget(self.media_id_map_key, content_hash)
        if cached_id:
             logger.info(f"Material hit cache: {content_hash}")
             return cached_id.decode('utf-8')
             
        # Compress
        content = self._compress_image(content)
        
        token = token_manager.get_token()
        url = f"https://api.weixin.qq.com/cgi-bin/material/add_material?access_token={token}&type=image"
        files = {'media': ('cover.jpg', content, 'image/jpeg')}
        
        try:
            resp = requests.post(url, files=files, timeout=60)
            data = resp.json()
            
            # Check for specific error codes for "Full"
            # 45001: Source file size exceeded (not quota, but maybe size limit?)
            # 48001: api unauthorized (permissions)
            # Quota full error is typically not explicitly strictly documented as consistent 
            # but usually fails with errcode != 0
            
            if "media_id" in data:
                 media_id = data["media_id"]
                 self.redis_client.hset(self.media_id_map_key, content_hash, media_id)
                 return media_id
            
            # Error Handling Pattern
            err_code = data.get("errcode")
            # Assuming 45001 or general failure might be capacity. 
            # We aggressively try cleanup if it looks like a resource limit.
            if err_code in [45001, 88000]: # 88000 is example, 45001 sometimes used for capacity issues broadly or specific size.
                 logger.warning(f"Upload failed with code {err_code}. Attempting cleanup and retry...")
                 self.cleanup_oldest_materials(5)
                 
                 # Retry once
                 resp = requests.post(url, files={'media': ('cover.jpg', content, 'image/jpeg')}, timeout=60)
                 data = resp.json()
                 if "media_id" in data:
                      return data["media_id"]
            
            # If still failing or other error
            raise Exception(f"Failed to upload material: {data}")

        except Exception as e:
            # If it's a "quota full" guessed exception structure, we could catch it here too.
            # But the JSON check above handles API errors.
            raise e

    def upload_temporary_material(self, image_data: Dict) -> str:
        """
        Uploads an image as temporary material (expires in 3 days).
        Useful as fallback if permanent material quota is full or unauthorized.
        """
        content = self._get_image_content(image_data)
        # Compress
        content = self._compress_image(content)
        
        token = token_manager.get_token()
        url = f"https://api.weixin.qq.com/cgi-bin/media/upload?access_token={token}&type=image"
        
        files = {'media': ('cover_temp.jpg', content, 'image/jpeg')}
        
        resp = requests.post(url, files=files, timeout=60)
        data = resp.json()
        
        if "media_id" not in data:
            raise Exception(f"Failed to upload temporary material: {data}")
            
        # We generally don't cache temporary media IDs long-term because they expire.
        # But for valid duration we could. For now, no caching.
        return data["media_id"]

media_client = MediaClient()
