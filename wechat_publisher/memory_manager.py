
import logging
from typing import List, Dict, Optional
from collections import deque
from .msg_logger import get_db_connection

logger = logging.getLogger("wechat_memory")

class MemoryManager:
    """
    Manages chat history for users.
    Strategy:
    1. In-Memory Cache (LRU per user)
    2. Fallback to DB (on cache miss)
    3. Update Cache & DB (DB update handled by logger, Cache is manual)
    """
    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        # Cache structure: openid -> list of messages
        # Message format: {"role": "user"|"model", "parts": ["text"]}
        self._cache: Dict[str, List[Dict]] = {}
        
    def get_context(self, openid: str, db_url: str = None) -> List[Dict]:
        """
        Retrieve context for a user.
        If not in cache, fetch from DB.
        """
        if openid in self._cache:
            return self._cache[openid]
            
        # Cache Miss: Fetch from DB
        logger.info(f"Cache miss for {openid}, fetching from DB...")
        history = self._fetch_from_db(openid, db_url)
        self._cache[openid] = history
        return history

    def update_context(self, openid: str, content: str, role: str, db_url: str = None):
        """
        Update local cache with new message.
        role: 'user' or 'model'
        """
        if openid not in self._cache:
             # Initialize cache first to ensure order
            self.get_context(openid, db_url=db_url)
            
        # Format for Gemini: {"role": role, "parts": [content]}
        msg_obj = {"role": role, "parts": [content]}
        
        self._cache[openid].append(msg_obj)
        
        # Maintain Size
        if len(self._cache[openid]) > self.max_history:
            self._cache[openid] = self._cache[openid][-self.max_history:]

    def _fetch_from_db(self, openid: str, db_url: str = None) -> List[Dict]:
        """
        Fetch last N messages from DB and convert to Gemini format.
        """
        if not db_url:
            return []
            
        conn = get_db_connection(db_url)
        if not conn:
            return []
            
        try:
            cursor = conn.cursor()
            # Fetch content, direction, create_time
            # direction: MO (User) -> 'user', MT (Bot) -> 'model'
            sql = """
            SELECT content, direction 
            FROM wechat_user_logs 
            WHERE openid = %s 
            ORDER BY create_time DESC 
            LIMIT %s
            """
            cursor.execute(sql, (openid, self.max_history))
            rows = cursor.fetchall()
            cursor.close()
            
            # DB returns Descending (Newest first), we need Ascending (Oldest first) for history
            rows.reverse()
            
            history = []
            for row in rows:
                content = row[0]
                direction = row[1]
                
                role = "user" if direction == "MO" else "model"
                history.append({"role": role, "parts": [content]})
                
            return history
        except Exception as e:
            logger.error(f"Failed to fetch history for {openid}: {e}")
            return []
        finally:
            if conn:
                conn.close()

# Global Instance
memory_manager = MemoryManager()
