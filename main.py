from fastapi import FastAPI, HTTPException, Body, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from starlette import status
from pydantic import BaseModel, Field
from typing import List, Optional, Union
import logging
import os
from dotenv import load_dotenv
from wechat_publisher import wechat_public_article, wechat_media_publish, draft_manager

# Load env for ADMIN_API_KEY
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

class ImageItem(BaseModel):
    image_index: int = Field(0, description="Index of the image.")
    image_type: str = Field(..., pattern="^(url|base64|path)$", description="Source type.")
    image_url: Optional[str] = None
    image_base64: Optional[str] = None
    media_path: Optional[str] = None # Support local path (for docker mapped volumes)
    image_alt: Optional[str] = None

class PublishRequest(BaseModel):
    article_markdown: str = Field(..., description="Markdown content.")
    images_list: List[ImageItem] = Field(..., description="List of images.")
    title: str = Field(..., description="Title.")
    author: str = Field("Animagent", description="Author.")
    digest: str = Field("", description="Summary.")
    cover_image_index: int = Field(1, description="Cover Image Index.")
    content_source_url: str = Field("", description="Source Link.")
    auto_publish: bool = Field(False, description="Publish immediately?")
    preview_wxname: str = Field("", description="Preview WeChat ID.")
    preview_email: str = Field("", description="Preview Email.")
    use_llm_parser: bool = Field(False, description="Use LLM for parsing? Default False (Regex).")

class MediaPublishRequest(BaseModel):
    media_type: str = Field(..., pattern="^(image|video|voice)$", description="Media Type.")
    media_source: ImageItem = Field(..., description="Media source info (url/base64/path).")
    title: str = Field("", description="Video Title (Required for Video).")
    introduction: str = Field("", description="Video Intro (Required for Video).")

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "2.0.0"}

@app.post("/publish", dependencies=[Depends(get_api_key)])
def publish_article_endpoint(request: PublishRequest):
    """
    Publishes an Article (Draft).
    """
    logger.info(f"Received Article Publish Request: {request.title}")
    
    # Validation logic (Cover must exist)
    if not request.images_list:
        raise HTTPException(status_code=400, detail="images_list cannot be empty.")

    # Force Cover Index to 1 if user logic requires it, or respect input?
    # User said "image_1 and image_10 replace issue". 
    # Let's trust the input cover_image_index but validation is good.
    
    try:
        images_data = [img.dict() for img in request.images_list]
        
        result = wechat_public_article(
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
            use_llm_parser=request.use_llm_parser
        )
        
        if not result['status']:
            raise HTTPException(status_code=500, detail=result.get('message', 'Unknown error'))
            
        return result
        
    except Exception as e:
        logger.error(f"Publish Endpoint Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/publish/media", dependencies=[Depends(get_api_key)])
def publish_media_endpoint(request: MediaPublishRequest):
    """
    Publishes Standalone Media (Image, Video, Voice) to Permanent Material.
    """
    logger.info(f"Received Media Publish Request: {request.media_type}")
    
    try:
        media_data = request.media_source.dict()
        
        result = wechat_media_publish(
            media_type=request.media_type,
            media_data=media_data,
            title=request.title,
            introduction=request.introduction
        )
        
        if not result['status']:
             raise HTTPException(status_code=500, detail=result.get('message'))
             
        return result

    except Exception as e:
        logger.error(f"Media Endpoint Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/approve")
async def approve_publish(media_id: str, key: str):
    EXPECTED_KEY = "secret_approval_key"
    if key != EXPECTED_KEY:
         return {"status": "error", "message": "Invalid Approval Key"}
         
    try:
        publish_id = draft_manager.publish_draft(media_id)
        return {"status": "success", "publish_id": publish_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5015)
