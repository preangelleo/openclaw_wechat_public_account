from fastapi import FastAPI, HTTPException, Body, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from starlette import status
from pydantic import BaseModel, Field
from typing import List, Optional, Union
import logging
import os
from dotenv import load_dotenv
from wechat_publisher import wechat_public_article

# Load env for ADMIN_API_KEY
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("wechat_service")

app = FastAPI(
    title="WeChat Public Account Publisher API",
    description="API for automating article publishing to WeChat Official Accounts.",
    version="1.0.0"
)

# Auth Configuration
API_KEY_NAME = "X-Admin-Api-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_api_key(api_key_header: str = Security(api_key_header)):
    """
    Validates the ADMIN_API_KEY from the header.
    """
    expected_key = os.getenv("ADMIN_API_KEY")
    if not expected_key:
        # If no key configured, we might want to warn or fail open/closed.
        # Closing is safer.
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
    image_index: int = Field(..., description="Index of the image in the sequence.")
    image_type: str = Field(..., pattern="^(url|base64)$", description="Type of image source: 'url' or 'base64'.")
    image_url: Optional[str] = Field(None, description="Public URL of the image (required if type='url').")
    image_base64: Optional[str] = Field(None, description="Base64 encoded string of the image (required if type='base64').")
    image_alt: Optional[str] = Field(None, description="Alt text for the image.")

class PublishRequest(BaseModel):
    article_markdown: str = Field(..., description="Markdown content of the article. Use tags like 'image_1' for image placement.")
    images_list: List[ImageItem] = Field(..., description="List of images referenced in the markdown.")
    title: str = Field(..., description="Title of the article.")
    author: str = Field("Animagent", description="Author name displayed in WeChat.")
    digest: str = Field("", description="Short summary/digest displayed in the article list.")
    cover_image_index: int = Field(1, description="Index of the image to be used as the cover thumbnail.")
    content_source_url: str = Field("", description="Original Article Link.")
    auto_publish: bool = Field(False, description="Whether to publish directly.")
    preview_wxname: str = Field("", description="WeChat ID to send preview to.")
    preview_email: str = Field("", description="Email address to send preview & approve link.")

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/publish", dependencies=[Depends(get_api_key)])
def publish_article_endpoint(request: PublishRequest):
    """
    Publishes an article to WeChat Public Account (Draft).
    Requires 'ADMIN_API_KEY' header for authentication.
    """
    logger.info(f"Received Publish Request: {request.title}")
    
    # Validation: Check image list
    if not request.images_list:
        raise HTTPException(status_code=400, detail="images_list cannot be empty. At least one image (Index 1) is required for Cover.")

    # Enforce Rule: Index 1 must exist (it is the Cover)
    img_indices = [img.image_index for img in request.images_list]
    if 1 not in img_indices:
        raise HTTPException(status_code=400, detail="Image Index 1 is missing. It is required for the Cover Image.")

    # Enforce Rule: Cover Image is ALWAYS Index 1
    # We ignore the user's cover_image_index if provided, or validate it.
    # The user instruction was "First one is cover... fix the rule".
    # So we force cover_image_index to 1.
    final_cover_index = 1

    try:
        # Convert Pydantic models to dicts for SDK
        images_data = [img.dict() for img in request.images_list]
        
        result = wechat_public_article(
            images_list=images_data,
            article_markdown=request.article_markdown,
            title=request.title,
            author=request.author,
            digest=request.digest,
            cover_image_index=final_cover_index,
            content_source_url=request.content_source_url,
            preview_wxname=request.preview_wxname,
            preview_email=request.preview_email,
            auto_publish=request.auto_publish
        )
        
        if not result['status']:
            raise HTTPException(status_code=500, detail=result.get('message', 'Unknown error'))
            
        return result
        
    except Exception as e:
        logger.error(f"Publish Endpoint Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/approve")
async def approve_publish(media_id: str, key: str):
    """
    Endpoint for One-Click Publish via Email.
    """
    # Simple security check
    # In production, use a rotating token or DB-stored nonce. 
    # For personal MVP, a fixed secret from .env is acceptable.
    EXPECTED_KEY = "secret_approval_key" # Should be sync with publisher.py
    
    if key != EXPECTED_KEY:
         return {"status": "error", "message": "Invalid Approval Key"}
         
    try:
        publish_id = draft_manager.publish_draft(media_id)
        return {
            "status": "success", 
            "message": "Article Published Successfully!", 
            "publish_id": publish_id
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    # Allow port to be configured via env or default to 5015
    uvicorn.run(app, host="0.0.0.0", port=5015)
