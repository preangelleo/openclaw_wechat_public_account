import os
from dotenv import load_dotenv

# Load environment variables explicitly if needed, though usually loaded by caller.
# Using find_dotenv to locate .env in parent directory if running from subdir
from dotenv import find_dotenv
load_dotenv(find_dotenv())

# WeChat Credentials
WECHAT_APPID = os.getenv("APPID")
WECHAT_APP_SECRET = os.getenv("SECRET")

# OpenRouter Credentials
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_HEADER_SITE_URL = os.getenv("OPENROUTER_HEADER_SITE_URL", "https://animagent.ai")
OPENROUTER_HEADER_SITE_NAME = os.getenv("OPENROUTER_HEADER_SITE_NAME", "Animagent.ai")

# External Services
REDIS_URL = os.getenv("REDIS_URL", "redis://animagent-redis:6379")

# Validation
if not WECHAT_APPID or not WECHAT_APP_SECRET:
    raise ValueError("Missing WeChat Credentials (APPID, SECRET) in .env")
