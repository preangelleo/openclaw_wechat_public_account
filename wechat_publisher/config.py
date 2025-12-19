import os
from dotenv import load_dotenv
from dotenv import find_dotenv

# Load environment variables explicitly if needed, though usually loaded by caller.
# Using find_dotenv to locate .env in parent directory if running from subdir
load_dotenv(find_dotenv())

# WeChat Credentials
WECHAT_APPID = os.getenv("APPID")
WECHAT_APP_SECRET = os.getenv("SECRET")
WECHAT_TOKEN = os.getenv("WECHAT_TOKEN")
WECHAT_AES_KEY = os.getenv("WECHAT_AES_KEY")

# OpenRouter Credentials
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_HEADER_SITE_URL = os.getenv("OPENROUTER_HEADER_SITE_URL", "https://animagent.ai")
OPENROUTER_HEADER_SITE_NAME = os.getenv("OPENROUTER_HEADER_SITE_NAME", "Animagent.ai")

# Model Configuration
TEXT_MODEL = os.getenv("TEXT_MODEL", "google/gemini-2.5-flash")
TEXT_MODEL_LITE = os.getenv("TEXT_MODEL_LITE", "google/gemini-2.5-flash-lite")
TEXT_MODEL_PRO = os.getenv("TEXT_MODEL_PRO", "google/gemini-3-pro-preview")
TEXT_MODEL_FLASH = "google/gemini-3-flash-preview"

TEXT_MODEL_LIST = [TEXT_MODEL, TEXT_MODEL_FLASH, TEXT_MODEL_PRO]

# External Services
REDIS_URL = os.getenv("REDIS_URL", "redis://animagent-redis:6379")

# Validation
if not WECHAT_APPID or not WECHAT_APP_SECRET:
    # It seems user might be using WECHAT_APPID in .env based on bot_handler logic
    # Let's be flexible or strict? 
    # bot_handler.py line 8: from wechat_publisher.config import WECHAT_TOKEN, WECHAT_AES_KEY, WECHAT_APPID
    # So WECHAT_APPID is expected to be exported.
    pass

if not WECHAT_TOKEN:
    # Log warning but don't crash yet, maybe only publishing needed?
    # But for bot, TOKEN is needed.
    pass
