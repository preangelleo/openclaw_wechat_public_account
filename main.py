from fastapi import FastAPI, HTTPException, Body, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from starlette import status
from pydantic import BaseModel, Field
from typing import List, Optional, Union
import logging
import os
from dotenv import load_dotenv
from wechat_publisher import wechat_public_article, wechat_media_publish, draft_manager

# Load env for ADMIN_API_KEY (Deployment Gateway Security Only)
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("wechat_service")

app = FastAPI(
    title="WeChat Public Account Publisher API",
    description="API for automating content publishing to WeChat Official Accounts.",
    version="2.0.0"
)

# Auth Configuration
API_KEY_NAME = "X-Admin-Api-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_api_key(api_key_header: str = Security(api_key_header)):
    expected_key = os.getenv("ADMIN_API_KEY")
    if not expected_key:
        logger.error("ADMIN_API_KEY not found in environment!")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server Authorization Configuration Error"
        )
        
    if api_key_header == expected_key:
        return api_key_header
        
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Could not validate credentials"
    )

class CredentialsDict(BaseModel):
    wx_appid: str = Field(..., description="WeChat App ID")
    wx_secret: str = Field(..., description="WeChat App Secret")
    wx_token: Optional[str] = Field(None, description="WeChat Token for Webhooks")
    wx_aes_key: Optional[str] = Field(None, description="WeChat AES Key for Webhooks")
    openrouter_api_key: Optional[str] = Field(None, description="OpenRouter API Key for Markdown parsing and chat")
    openrouter_text_model: Optional[str] = Field(None, description="Optional specific model ID to use on OpenRouter (e.g., 'google/gemini-2.5-flash').")
    db_url: Optional[str] = Field(None, description="PostgreSQL or Redis URL for state/sync")

class ImageItem(BaseModel):
    image_index: int = Field(0, description="Index of the image.")
    image_type: str = Field(..., pattern="^(url|base64|path)$", description="Source type.")
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    media_path: Optional[str] = None # Support local path (for docker mapped volumes)
    image_alt: Optional[str] = None

class UnifiedPublishRequest(BaseModel):
    # Common
    publish_type: str = Field("article", pattern="^(article|image|video|voice)$", description="Type of content to publish.")
    
    # For Article
    article_markdown: Optional[str] = Field(None, description="Markdown content (Article only).")
    images_list: Optional[List[ImageItem]] = Field(None, description="List of images (Article only).")
    author: str = Field("Animagent", description="Author.")
    digest: str = Field("", description="Summary.")
    cover_image_index: int = Field(1, description="Cover Image Index.")
    content_source_url: str = Field("", description="Source Link.")
    auto_publish: bool = Field(False, description="Publish immediately?")
    preview_wxname: str = Field("", description="Preview WeChat ID.")
    preview_email: str = Field("", description="Preview Email.")
    use_llm_parser: bool = Field(True, description="Use LLM Parser? Default True for better structure.")
    audio_url: Optional[str] = Field(None, description="URL of the audio file to insert at the top of the article.")
    audio_size: Optional[int] = Field(None, description="Size of the audio file in bytes.")
    audio_duration: Optional[int] = Field(None, description="Duration of the audio file in seconds.")

    # For Media (Image/Video/Voice)
    title: str = Field("", description="Title (Required for Article/Video).")
    introduction: str = Field("", description="Introduction (Required for Video).")
    media_source: Optional[ImageItem] = Field(None, description="Media source info (For single media publish).")
    
    # Credentials
    credentials: CredentialsDict = Field(..., description="Dynamic credentials for operations.")

@app.post("/publish", dependencies=[Depends(get_api_key)])
async def publish_endpoint(request: UnifiedPublishRequest):
    """
    Unified Publish Endpoint.
    Supports: article (draft), image, video, voice (permanent material).
    """
    logger.info(f"Received Publish Request: {request.publish_type}")
    
    try:
        if request.publish_type == "article":
            # Validation
            if not request.images_list:
                raise HTTPException(status_code=400, detail="images_list cannot be empty for article.")
            
            images_data = [img.dict() for img in request.images_list]
            result = await wechat_public_article(
                images_list=images_data,
                article_markdown=request.article_markdown,
                title=request.title,
                author=request.author,
                digest=request.digest,
                cover_image_index=request.cover_image_index,
                content_source_url=request.content_source_url,
                preview_wxname=request.preview_wxname,
                preview_email=request.preview_email,
                auto_publish=request.auto_publish,
                use_llm_parser=request.use_llm_parser,
                audio_url=request.audio_url,
                audio_size=request.audio_size,
                audio_duration=request.audio_duration,
                wx_appid=request.credentials.wx_appid,
                wx_secret=request.credentials.wx_secret,
                openrouter_api_key=request.credentials.openrouter_api_key,
                openrouter_text_model=request.credentials.openrouter_text_model,
                db_url=request.credentials.db_url
            )
        else:
            # Media Publish
            if not request.media_source:
                raise HTTPException(status_code=400, detail="media_source is required for media publish.")
                
            media_data = request.media_source.dict()
            result = wechat_media_publish(
                media_type=request.publish_type,
                media_data=media_data,
                title=request.title,
                introduction=request.introduction,
                wx_appid=request.credentials.wx_appid,
                wx_secret=request.credentials.wx_secret,
                db_url=request.credentials.db_url
            )
            
        if not result['status']:
            raise HTTPException(status_code=500, detail=result.get('message', 'Unknown error'))
            
        return result
        
    except Exception as e:
        logger.error(f"Publish Endpoint Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/approve")
async def approve_publish(media_id: str, key: str, wx_appid: str, wx_secret: str, db_url: str = None):
    EXPECTED_KEY = "secret_approval_key"
    if key != EXPECTED_KEY:
         return {"status": "error", "message": "Invalid Approval Key"}
         
    try:
        publish_id = draft_manager.publish_draft(wx_appid, wx_secret, media_id, db_url)
        return {"status": "success", "publish_id": publish_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/health")
def health_check():
    return {"status": "ok"}



# Import Router
from wechat_publisher.router import router as wechat_bot_router

# Nginx strips the /api/weixin-publish prefix, so we expose /wechat/callback at root level relative to the app
app.include_router(wechat_bot_router, tags=["WeChat Bot"])

# Scheduler Configuration (Hourly Sync)
# To keep the service stateless, automated background syncing that relies on globally loaded credentials
# is removed from the Open Source entrypoint, as it requires a specific account's credentials.
# Users who want syncing should execute a sync script passing their credentials.
logger.info("Stateless mode: Auto-sync background scheduler disabled. Pass db_url to endpoints if sync context is desired during operations.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5015)
