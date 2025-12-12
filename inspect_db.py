
import os
import psycopg2
import logging

# Defaults from msg_logger.py / README
DB_NAME = "animagent_backend_api"
DB_USER = "animagent_admin"
DB_PASS = "BD_H_-nYH6dXBzZRt8Py2YQdPkhqNhYt"
DB_HOST = "localhost"

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def connect_and_query(port):
    try:
        logger.info(f"Attempting connection to {DB_HOST}:{port}...")
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=port
        )
        logger.info(f"Connected successfully on port {port}!")
        return conn
    except Exception as e:
        logger.warning(f"Connection failed on port {port}: {e}")
        return None

def inspect_tables(conn):
    cursor = conn.cursor()
    
    # 1. Check Tables
    logger.info("-" * 30)
    logger.info("CHECKING TABLES")
    cursor.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    tables = cursor.fetchall()
    table_names = [t[0] for t in tables]
    logger.info(f"Found tables: {table_names}")

    # 2. Check wechat_published_articles
    if 'wechat_published_articles' in table_names:
        logger.info("-" * 30)
        logger.info("CHECKING: wechat_published_articles")
        cursor.execute("SELECT COUNT(*) FROM wechat_published_articles")
        count = cursor.fetchone()[0]
        logger.info(f"Total Articles: {count}")
        
        if count > 0:
            cursor.execute("SELECT title, update_time FROM wechat_published_articles ORDER BY update_time DESC LIMIT 5")
            rows = cursor.fetchall()
            logger.info("Latest 5 Articles:")
            for row in rows:
                logger.info(f" - [{row[1]}] {row[0]}")
    else:
        logger.warning("Table 'wechat_published_articles' NOT FOUND!")

    # 3. Check wechat_user_logs
    if 'wechat_user_logs' in table_names:
        logger.info("-" * 30)
        logger.info("CHECKING: wechat_user_logs")
        cursor.execute("SELECT COUNT(*) FROM wechat_user_logs")
        count = cursor.fetchone()[0]
        logger.info(f"Total User Logs: {count}")
        
        if count > 0:
            cursor.execute("SELECT openid, content, create_time FROM wechat_user_logs ORDER BY create_time DESC LIMIT 5")
            rows = cursor.fetchall()
            logger.info("Latest 5 Logs:")
            for row in rows:
                logger.info(f" - [{row[2]}] {row[0]}: {row[1]}")
    else:
        logger.warning("Table 'wechat_user_logs' NOT FOUND!")

    conn.close()

def main():
    # Try 5010 first, then 5432
    conn = connect_and_query(5010)
    if not conn:
        conn = connect_and_query(5432)
    
    if conn:
        inspect_tables(conn)
    else:
        logger.error("Could not connect to database on port 5010 or 5432.")

if __name__ == "__main__":
    main()
