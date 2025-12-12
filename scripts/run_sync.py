
import sys
import os
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(level=logging.INFO)

from wechat_publisher.sync_service import sync_service

if __name__ == "__main__":
    print("Starting Article Sync...")
    count = sync_service.sync_recent_articles(limit=20)
    print(f"Finished. Synced {count} batches (approx {count} items).")
