import logging
import requests
import json
import time
import psycopg2
from typing import List, Dict, Optional
from .token_manager import token_manager

logger = logging.getLogger(__name__)

def get_db_connection(db_url: str):
    if not db_url:
        return None
    try:
        conn = psycopg2.connect(db_url)
        return conn
    except Exception as e:
        logger.error(f"DB Connection failed: {e}")
        return None

class ArticleSyncService:
    def __init__(self):
        pass
        
    def get_published_articles(self, appid: str, secret: str, redis_url: str = None, offset: int = 0, count: int = 20) -> List[Dict]:
        """
        Fetch articles using 'material/batchget_material' (Permanent Assets).
        Type = 'news' (Graphic Messages / Articles).
        """
        token = token_manager.get_token(appid, secret, redis_url)
        url = f"https://api.weixin.qq.com/cgi-bin/material/batchget_material?access_token={token}"
        
        payload = {
            "type": "news",
            "offset": offset,
            "count": count
        }
        
        try:
            resp = requests.post(url, json=payload, timeout=30)
            resp.encoding = 'utf-8' # Force usage of UTF-8 for WeChat API
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

    def sync_recent_articles(self, appid: str, secret: str, limit: int = 10, db_url: str = None, redis_url: str = None):
        logger.info(f"Starting Article Sync (Limit={limit})...")
        if not db_url:
            logger.warning("No db_url provided for Article Sync. Skipping.")
            return 0
            
        conn = get_db_connection(db_url)
        if not conn:
            return 0
            
        new_items_count = 0
        current_offset = 0
        
        try:
            while current_offset < limit:
                # Calculate batch size (WeChat max 20)
                batch_size = min(20, limit - current_offset)
                
                logger.info(f"Fetching batch [Offset: {current_offset}, Count: {batch_size}]...")
                items = self.get_published_articles(appid, secret, redis_url=redis_url, offset=current_offset, count=batch_size)
                
                if not items:
                    logger.info("No more items returned from WeChat.")
                    break
                
                # Check for empty list if API returns success but empty 'item'
                if len(items) == 0:
                    break

                # Process this batch
                for item in items:
                    media_id = item.get("media_id")
                    content = item.get("content", {})
                    news_items = content.get("news_item", [])
                    update_time = item.get("update_time")
                    
                    for idx, news in enumerate(news_items):
                        article_unique_id = f"{media_id}_{idx}"
                        
                        # Check DB
                        try:
                            check_cursor = conn.cursor()
                            check_cursor.execute("SELECT 1 FROM wechat_published_articles WHERE article_id = %s", (article_unique_id,))
                            exists = check_cursor.fetchone()
                            check_cursor.close()
                            
                            if exists:
                                continue # Skip existing
                                
                            # Insert New
                            logger.info(f"Found NEW Article: {news.get('title')}")
                            
                            insert_sql = """
                            INSERT INTO wechat_published_articles 
                            (article_id, title, digest, content_url, thumb_url, author, update_time)
                            VALUES (%s, %s, %s, %s, %s, %s, %s)
                            """
                            insert_cursor = conn.cursor()
                            insert_cursor.execute(insert_sql, (
                                article_unique_id, 
                                news.get("title"), 
                                news.get("digest"), 
                                news.get("url"), 
                                news.get("thumb_url"), 
                                news.get("author"), 
                                update_time
                            ))
                            conn.commit() # Commit each insert to be safe
                            insert_cursor.close()
                            new_items_count += 1
                            
                        except Exception as inner_e:
                            logger.error(f"Error processing article: {inner_e}")
                            conn.rollback()

                # Increment offset for next loop
                current_offset += len(items)
                
                # Safety break to avoid infinite loops if something is weird
                if len(items) < batch_size:
                    # If we got fewer than requested, we are at the end
                    break
                    
        except Exception as e:
            logger.error(f"Sync process interrupted: {e}")
        finally:
            if conn:
                conn.close()

        logger.info(f"Sync Complete. Added {new_items_count} new articles.")
        return new_items_count

    def search_articles(self, keyword: str, db_url: str = None) -> List[Dict]:
        """
        Search articles by keyword (Title or Digest).
        Returns list of top 5 matches.
        """
        if not db_url:
            return []
            
        conn = get_db_connection(db_url)
        if not conn:
            return []
            
        search_pattern = f"%{keyword}%"
        try:
            cursor = conn.cursor()
            # Search Title OR Digest
            sql = """
            SELECT title, digest, content_url, thumb_url, update_time 
            FROM wechat_published_articles 
            WHERE title ILIKE %s OR digest ILIKE %s
            ORDER BY update_time DESC 
            LIMIT 5
            """
            cursor.execute(sql, (search_pattern, search_pattern))
            rows = cursor.fetchall()
            cursor.close()
            
            results = []
            for row in rows:
                results.append({
                    "title": row[0],
                    "description": row[1] or "", # Digest can be null
                    "url": row[2],
                    "picurl": row[3]
                })
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
        finally:
            if conn:
                conn.close()
            
        return []

# Global Instance
sync_service = ArticleSyncService()
