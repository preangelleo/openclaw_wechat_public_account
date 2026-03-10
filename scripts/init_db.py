
import os
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv

load_dotenv()

# Database Config from .env
# Database Config from .env or defaults
DB_NAME = os.getenv("POSTGRES_DB", "openclaw_wechat_public_account")
DB_USER = os.getenv("POSTGRES_USER", "openclaw_wechat_public_account")
DB_PASS = os.getenv("POSTGRES_PASSWORD", "your_db_password_here")
DB_HOST = os.getenv("POSTGRES_HOST", "localhost")
DB_PORT = os.getenv("POSTGRES_PORT", "5010")

def create_table():
    print(f"Connecting to DB {DB_NAME} at {DB_HOST}:{DB_PORT}...")
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.autocommit = True
        cur = conn.cursor()
        
        # Create Table
        create_sql = """
        CREATE TABLE IF NOT EXISTS wechat_published_articles (
            article_id VARCHAR(255) PRIMARY KEY, 
            title TEXT NOT NULL,
            digest TEXT,
            content_url TEXT NOT NULL, 
            thumb_url TEXT,
            cover_url TEXT, 
            author TEXT,
            is_deleted BOOLEAN DEFAULT FALSE,
            update_time BIGINT,
            create_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cur.execute(create_sql)
        print("✅ Table `wechat_published_articles` created/verified.")
        
        # Create User Logs Table
        log_table_sql = """
        CREATE TABLE IF NOT EXISTS wechat_user_logs (
            log_id SERIAL PRIMARY KEY,
            openid VARCHAR(64) NOT NULL,
            msg_type VARCHAR(20),
            content TEXT,
            direction VARCHAR(10), -- 'MO' or 'MT'
            create_time BIGINT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cur.execute(log_table_sql)
        print("✅ Table `wechat_user_logs` created/verified.")
        
        # Create Index
        index_sql = "CREATE INDEX IF NOT EXISTS idx_wechat_articles_title ON wechat_published_articles(title);"
        cur.execute(index_sql)
        
        log_index_sql = "CREATE INDEX IF NOT EXISTS idx_user_logs_openid ON wechat_user_logs(openid);"
        cur.execute(log_index_sql)
        print("✅ Indexes created/verified.")
        
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Database Error: {e}")

if __name__ == "__main__":
    create_table()
