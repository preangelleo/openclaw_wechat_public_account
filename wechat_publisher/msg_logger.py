
import logging
import os
import time
import psycopg2
import sys
from typing import Optional

logger = logging.getLogger(__name__)

def get_db_connection(db_url: str):
    if not db_url:
        return None
    try:
        conn = psycopg2.connect(db_url)
        return conn
    except Exception as e:
        err_msg = f"DB Connection failed: {e}"
        logger.error(err_msg)
        print(f"CRITICAL: {err_msg}", file=sys.stderr) # Force Output
        return None

def log_message(openid: str, content: str, msg_type: str = "text", direction: str = "MO", db_url: str = None):
    """
    Logs a message to DB.
    direction: 'MO' (User Sent) or 'MT' (Reply/Bot Sent)
    """
    print(f"Attempting to log message: {direction} from {openid}", file=sys.stdout) # Debug
    if not db_url:
        print("Log skipped: No DB Connection URL provided", file=sys.stderr)
        return
        
    conn = get_db_connection(db_url)
    if not conn:
        print("Log skipped: No DB Connection", file=sys.stderr)
        return
        
    try:
        cursor = conn.cursor()
        create_time = int(time.time())
        
        sql = """
        INSERT INTO wechat_user_logs (openid, msg_type, content, direction, create_time)
        VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (openid, msg_type, content, direction, create_time))
        conn.commit()
        cursor.close()
        logger.info(f"Logged {direction} message for {openid}")
        print(f"SUCCESS: Logged {direction} message for {openid}", file=sys.stdout)
    except Exception as e:
        err_msg = f"Failed to log message for {openid}: {e}"
        logger.error(err_msg)
        print(f"ERROR: {err_msg}", file=sys.stderr)
    finally:
        if conn:
            conn.close()
