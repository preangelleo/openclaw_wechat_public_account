
import logging
import os
import time
import psycopg2
from typing import Optional
# Reuse connection logic or import? Better to keep it clean.
# We will duplicate simple connection logic or move to a common db helper if this grows.
# For now, let's just use the same env var logic.

logger = logging.getLogger(__name__)

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
        logger.error(f"DB Connection failed: {e}")
        return None

def log_message(openid: str, content: str, msg_type: str = "text", direction: str = "MO"):
    """
    Logs a message to DB.
    direction: 'MO' (User Sent) or 'MT' (Reply/Bot Sent)
    """
    conn = get_db_connection()
    if not conn:
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
        # logger.info(f"Logged {direction} message for {openid}")
    except Exception as e:
        logger.error(f"Failed to log message for {openid}: {e}")
    finally:
        if conn:
            conn.close()

# Decorator? Or just direct call. Direct call is simpler.
