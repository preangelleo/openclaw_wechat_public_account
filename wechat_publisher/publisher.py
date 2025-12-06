import logging
import time
from typing import List, Dict, Any
from .media_client import media_client
from .llm_client import llm_client
from .draft_manager import draft_manager
from .gmail_functions import send_preview_email

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def wechat_public_article(
    images_list: List[Dict[str, Any]],
    article_markdown: str,
    title: str = "New Article", # We might need to extract title from markdown if not provided?
    author: str = "Animagent",
    digest: str = "",
    cover_image_index: int = 1,
    content_source_url: str = "",
    preview_wxname: str = "",
    preview_email: str = "",
    auto_publish: bool = False
) -> Dict[str, Any]:
    """
    Main SDK function to publish an article to WeChat Public Account.
    
    Steps:
    1. Upload all images to WeChat (get URLs).
    2. Upload cover image to WeChat (get Media ID).
    3. Generate structured Content via LLM.
    4. Render HTML.
    5. Create Draft.
    6. (Optional) Publish Draft.
    """
    
    try:
        # 1. Image Processing
        logger.info("Step 1: Processing Images...")
        image_url_map = {} # index -> wechat_url
        cover_media_id = None
        
        for img_info in images_list:
            idx = img_info.get('image_index')
            try:
                # Upload for Article Body
                wechat_url = media_client.upload_image_for_article(img_info)
                image_url_map[idx] = wechat_url
                
                # Check if this is the cover
                if idx == cover_image_index:
                    logger.info(f"Uploading Cover Image (Index: {idx})...")
                    try:
                        cover_media_id = media_client.upload_permanent_material(img_info)
                    except Exception as e:
                        logger.warning(f"Permanent material upload failed: {e}. Trying temporary material...")
                        # Fallback to temporary material
                        if "48001" in str(e) or "unauthorized" in str(e).lower():
                            cover_media_id = media_client.upload_temporary_material(img_info)
                        else:
                            raise e
                    
            except Exception as e:
                logger.error(f"Failed to upload image {idx}: {e}")
                # Continue? Or fail? Let's verify if critical.
                # If cover fails, we probably can't proceed.
                if idx == cover_image_index:
                    raise Exception(f"Failed to upload Cover Image {idx}: {e}")
        
        if not cover_media_id:
            logger.warning("No cover image set or found! Using first available image as fallback if possible.")
            # Fallback logic could be added here
            if image_url_map and images_list:
                 first_idx = images_list[0]['image_index']
                 cover_media_id = media_client.upload_permanent_material(images_list[0])
            else:
                 raise Exception("No images provided for cover.")

        # 2. LLM Processing
        logger.info("Step 2: Structuring Content via LLM...")
        structured_content = llm_client.process_article_content(article_markdown)
        
        # 3. HTML Rendering
        logger.info("Step 3: Rendering HTML...")
        content_html = draft_manager._render_html(structured_content, image_url_map)
        
        # 4. Draft Creation
        logger.info("Step 4: Creating WeChat Draft...")
        # If title/digest missing, try to get from markdown? 
        # For now assume passed in or use defaults.
        # If LLM parsed a title (h1), maybe we can overwrite? 
        # But SDK params usually take precedence.
        
        draft_media_id = draft_manager.create_draft(
            title=title,
            author=author,
            digest=digest,
            content_html=content_html,
            thumb_media_id=cover_media_id,
            content_source_url=content_source_url
        )
        logger.info(f"Draft Created! Media ID: {draft_media_id}")
        
        result = {
            "status": True,
            "message": "success",
            "draft_media_id": draft_media_id
        }
        
        # 4.5 Preview (Optional)
        if preview_wxname:
            logger.info(f"Sending Preview to {preview_wxname}...")
            draft_manager.send_preview(draft_media_id, preview_wxname)

        if preview_email:
            logger.info(f"Sending Email Preview to {preview_email}...")
            draft_link = draft_manager.get_draft_url(draft_media_id)
            if draft_link:
                # Construct Publish Action Link
                # Using a 'key' for simple security is good practice but for MVP we assume Admin API Key header 
                # or just open endpoint if user requests simple GET.
                # Let's create a specialized link.
                base_host = "https://animagent.ai"
                # TODO: Retrieve from env or config
                
                # We need an endpoint like /api/weixin-publish/approve?media_id=...&key=...
                # Using a hardcoded secret for now for the approval link security
                approval_key = "secret_approval_key" # Should be in .env
                publish_endpoint = f"{base_host}/api/weixin-publish/approve?media_id={draft_media_id}&key={approval_key}"
                
                send_preview_email(preview_email, draft_link, publish_endpoint, title)
            else:
                logger.warning("Could not get Draft URL, skipping email.")

        # 5. Publish
        if auto_publish:
            logger.info("Step 5: Publishing Draft...")
            publish_id = draft_manager.publish_draft(draft_media_id)
            result["publish_id"] = publish_id
            result["message"] = "success_published_pending" # pending audit
            logger.info(f"Publish Submitted. ID: {publish_id}")
            
        return result
        
    except Exception as e:
        logger.error(f"WeChat Publish Failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "status": False,
            "message": str(e)
        }
