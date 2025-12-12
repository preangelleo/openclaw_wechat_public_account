import logging
import requests
import json
import os
import time
import psycopg2
from typing import List, Dict, Optional
from .token_manager import token_manager
from .config import WECHAT_APPID

logger = logging.getLogger(__name__)

# Database Config (Reused for simplicity, should be in config but env vars are global)
# Database Config
DB_NAME = os.getenv("POSTGRES_DB", "animagent_backend_api")
DB_USER = os.getenv("POSTGRES_USER", "animagent_admin")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "BD_H_-nYH6dXBzZRt8Py2YQdPkhqNhYt")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5010")

def get_db_connection():
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT
        )
        return conn
    except Exception as e:
        logger.error(f"DB Connection failed to {host}:{port}: {e}")
        return None

class ArticleSyncService:
    def __init__(self):
        pass
        
    def get_published_articles(self, offset: int = 0, count: int = 20) -> List[Dict]:
        """
        Fetch articles using 'material/batchget_material' (Permanent Assets).
        Type = 'news' (Graphic Messages / Articles).
        """
        token = token_manager.get_token()
        url = f"https://api.weixin.qq.com/cgi-bin/material/batchget_material?access_token={token}"
        
        payload = {
            "type": "news",
            "offset": offset,
            "count": count
        }
        
        try:
            resp = requests.post(url, json=payload, timeout=30)
            data = resp.json()
            
            if "errcode" in data and data["errcode"] != 0:
                logger.error(f"WeChat API Error: {data}")
                return []
                
            return data.get("item", []) # 'item' is a list of news objects
            
        except Exception as e:
            logger.error(f"Failed to fetch articles: {e}")
            return []

    def save_article_to_db(self, conn, article_item):
        """
        Parses a single 'item' from batchget and saves its articles to DB.
        Note: One 'item' (media_id) can contain MULTIPLE articles (multi-graphic).
        """
        media_id = article_item.get("media_id")
        update_time = article_item.get("update_time")
        content = article_item.get("content", {})
        news_items = content.get("news_item", [])
        
        cursor = conn.cursor()
        
        for idx, news in enumerate(news_items):
            # Unique ID: media_id + index? Or just use url hash? 
            # Ideally media_id is for the "Group" of articles. 
            # If we want to reply with a specific article, we need valid data.
            # But wait, 'mpnews' reply takes 'media_id'. It sends the WHOLE group.
            # 'news' reply (link card) takes title/desc/url/picurl. It can point to one specific article in the group.
            
            # Let's save each article individually.
            # ID: {media_id}_{idx}
            article_unique_id = f"{media_id}_{idx}"
            title = news.get("title")
            url = news.get("url")
            thumb_url = news.get("thumb_url")
            digest = news.get("digest")
            author = news.get("author")
            
            # Upsert
            sql = """
            INSERT INTO wechat_published_articles 
            (article_id, title, digest, content_url, thumb_url, author, update_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (article_id) DO UPDATE SET
            title = EXCLUDED.title,
            digest = EXCLUDED.digest,
            content_url = EXCLUDED.content_url,
            thumb_url = EXCLUDED.thumb_url,
            update_time = EXCLUDED.update_time;
            """
            
            try:
                cursor.execute(sql, (
                    article_unique_id, title, digest, url, thumb_url, author, update_time
                ))
            except Exception as e:
                logger.error(f"Failed to insert article {title}: {e}")
        
        conn.commit()
        cursor.close()

    def sync_recent_articles(self, limit: int = 20):
        logger.info(f"Syncing up to {limit} recent articles...")
        conn = get_db_connection()
        if not conn:
            return 0
            
        # We fetch in batches of 20
        count_synced = 0
        offset = 0
        batch_size = 20
        
        while count_synced < limit:
            items = self.get_published_articles(offset, batch_size)
            if not items:
                break
                
            for item in items:
                self.save_article_to_db(conn, item)
                
            count_synced += len(items)
            offset += len(items)
            
            if len(items) < batch_size: # End of list
                break
                
        conn.close()
        logger.info(f"Synced {count_synced} items (groups).")
        return count_synced

    def search_article(self, keyword: str) -> Optional[Dict]:
        """
        Search for an article in local DB by title match.
        Returns dictionary with title, digest, url, thumb_url.
        """
        conn = get_db_connection()
        if not conn:
            return None
            
        cursor = conn.cursor()
        # Simple suffix/prefix match
        sql = "SELECT title, digest, content_url, thumb_url FROM wechat_published_articles WHERE title ILIKE %s ORDER BY update_time DESC LIMIT 1;"
        import urllib.parse
        
        try:
            cursor.execute(sql, (f"%{keyword}%",))
            row = cursor.fetchone()
            if row:
                return {
                    "title": row[0],
                    "description": row[1] or "No description",
                    "url": row[2],
                    "picurl": row[3] or "" # Fallback image?
                }
        except Exception as e:
            logger.error(f"Search failed: {e}")
        finally:
            cursor.close()
            conn.close()
            
        return None

# Global Instance
sync_service = ArticleSyncService()
