import logging
import time
from typing import List, Dict, Any, Optional
from .media_client import media_client
from .llm_client import llm_client
from .markdown_parser import markdown_parser
from .draft_manager import draft_manager
from .gmail_functions import send_preview_email

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def wechat_public_article(
    images_list: List[Dict[str, Any]],
    article_markdown: str,
    title: str = "New Article",
    author: str = "Animagent",
    digest: str = "",
    cover_image_index: int = 1,
    content_source_url: str = "",
    preview_wxname: str = "",
    preview_email: str = "",
    auto_publish: bool = False,
    use_llm_parser: bool = False, # Default to False (Regex) for robustness
    audio_url: str = None,
    audio_size: int = None,
    audio_duration: int = None,
    wx_appid: str = None,
    wx_secret: str = None,
    openrouter_api_key: str = None,
    openrouter_text_model: str = None,
    db_url: str = None
) -> Dict[str, Any]:
    """
    Main SDK function to publish an article to WeChat Public Account.
    """
    
    try:
        # 1. Audio Processing (Download & Upload)
        audio_media_id = None
        if audio_url:
            logger.info(f"Processing Audio: {audio_url}")
            
            # Check Limits (2MB and 60s)
            skip_audio = False
            limit_size = 2 * 1024 * 1024 # 2MB
            limit_duration = 60 # 60 seconds
            
            if audio_size and audio_size > limit_size:
                logger.warning(f"Audio size ({audio_size} bytes) exceeds WeChat limit ({limit_size} bytes). Skipping audio.")
                skip_audio = True
            
            if audio_duration and audio_duration > limit_duration:
                logger.warning(f"Audio duration ({audio_duration} s) exceeds WeChat limit ({limit_duration} s). Skipping audio.")
                skip_audio = True
                
            if not skip_audio:
                try:
                    # Reuse media_client which supports uploading from URL if type='url'
                    # But wait, upload_permanent_material expects a dict
                    audio_data = {
                        "image_type": "url", # Legacy key name used in media_client._get_bytes_content
                        "media_url": audio_url
                    }
                    audio_media_id = media_client.upload_permanent_material(
                        wx_appid, wx_secret,
                        audio_data, 
                        material_type="voice",
                        redis_url=db_url
                    )
                    logger.info(f"Audio uploaded successfully. Media ID: {audio_media_id}")
                except Exception as e:
                    logger.error(f"Failed to upload audio: {e}")
                    # Optional: Decide if we should fail the whole process or just skip audio
                    # User asked: "如果这个新功能能支持的话，我们就可以改" implies it's a feature.
                    # If audio is provided but fails, maybe we should error out?
                    # Let's log error and continue without audio for robustness, or raise?
                    # "用户上传了音频，我们也只支持一个音频，那这个 audio 呢，就应该插到文章的一开头"
                    # Raising error seems safer so user knows audio failed.
                    raise Exception(f"Failed to process audio: {e}")
            else:
                 logger.info("Audio skipped due to limits.")

        # 2. Image Processing
        logger.info("Step 1: Processing Images...")
        image_url_map = {} # index -> wechat_url
        cover_media_id = None
        
        for img_info in images_list:
            idx = img_info.get('image_index')
            try:
                # Upload for Article Body
                wechat_url = media_client.upload_image_for_article(wx_appid, wx_secret, img_info, redis_url=db_url)
                image_url_map[idx] = wechat_url
                
                # Check if this is the cover
                if idx == cover_image_index:
                    logger.info(f"Uploading Cover Image (Index: {idx})...")
                    try:
                        cover_media_id = media_client.upload_permanent_material(wx_appid, wx_secret, img_info, redis_url=db_url)
                    except Exception as e:
                        logger.warning(f"Permanent material upload failed: {e}. Trying temporary material...")
                        if "48001" in str(e) or "unauthorized" in str(e).lower():
                            cover_media_id = media_client.upload_temporary_material(wx_appid, wx_secret, img_info, redis_url=db_url)
                        else:
                            raise e
            except Exception as e:
                logger.error(f"Failed to upload image {idx}: {e}")
                if idx == cover_image_index:
                    raise Exception(f"Failed to upload Cover Image {idx}: {e}")
        
        if not cover_media_id:
            logger.warning("No cover image set or found! Using first available image as fallback if possible.")
            if image_url_map and images_list:
                 first_idx = images_list[0]['image_index']
                 cover_media_id = media_client.upload_permanent_material(wx_appid, wx_secret, images_list[0], redis_url=db_url)
            else:
                 raise Exception("No images provided for cover.")

        # 2. Content Structure (Regex vs LLM)
        logger.info(f"Step 2: Structuring Content (LLM Mode: {use_llm_parser})...")
        if use_llm_parser:
             structured_content = await llm_client.process_article_content(article_markdown, openrouter_api_key, openrouter_text_model)
        else:
             # Use robust regex parser
             structured_content = markdown_parser.parse_content(article_markdown)
        
        # 3. HTML Rendering
        logger.info("Step 3: Rendering HTML...")
        content_html = draft_manager._render_html(structured_content, image_url_map)
        
        # 4. Draft Creation
        logger.info("Step 4: Creating WeChat Draft...")
        draft_media_id = draft_manager.create_draft(
            appid=wx_appid,
            secret=wx_secret,
            title=title,
            author=author,
            digest=digest,
            content_html=content_html,
            thumb_media_id=cover_media_id,
            content_source_url=content_source_url,
            audio_media_id=audio_media_id,
            redis_url=db_url
        )
        logger.info(f"Draft Created! Media ID: {draft_media_id}")
        
        result = {
            "status": True,
            "message": "success",
            "draft_media_id": draft_media_id
        }
        
        # 4.5 Preview
        if preview_wxname:
            logger.info(f"Sending Preview to {preview_wxname}...")
            draft_manager.send_preview(appid=wx_appid, secret=wx_secret, media_id=draft_media_id, wxname=preview_wxname, redis_url=db_url)

        if preview_email:
            logger.info(f"Sending Email Preview to {preview_email}...")
            draft_link = draft_manager.get_draft_url(appid=wx_appid, secret=wx_secret, media_id=draft_media_id, redis_url=db_url)
            if draft_link:
                base_host = "https://animagent.ai"
                approval_key = "secret_approval_key"
                publish_endpoint = f"{base_host}/api/weixin-publish/approve?media_id={draft_media_id}&key={approval_key}"
                try:
                    send_preview_email(preview_email, draft_link, publish_endpoint, title)
                    logger.info(f"Checking email sending logic triggered for known recipient {preview_email}")
                except Exception as e:
                    logger.error(f"Error calling send_preview_email: {e}")
            else:
                logger.warning("Could not get Draft URL after retries, skipping email.")

        # 5. Publish
        if auto_publish:
            logger.info("Step 5: Publishing Draft...")
            publish_id = draft_manager.publish_draft(appid=wx_appid, secret=wx_secret, media_id=draft_media_id, redis_url=db_url)
            result["publish_id"] = publish_id
            result["message"] = "success_published_pending"
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

def wechat_media_publish(
    media_type: str, # image, video, voice
    media_data: Dict[str, Any],
    title: str = "",
    introduction: str = "",
    wx_appid: str = None,
    wx_secret: str = None,
    db_url: str = None
) -> Dict[str, Any]:
    """
    Publishes standalone media assets to WeChat (Permanent Material).
    Returns media_id.
    """
    try:
        logger.info(f"Uploading {media_type}...")
        media_id = media_client.upload_permanent_material(
            wx_appid, wx_secret,
            media_data, 
            material_type=media_type, 
            title=title, 
            introduction=introduction,
            redis_url=db_url
        )
        return {
            "status": True,
            "message": "success",
            "media_id": media_id,
            "type": media_type
        }
    except Exception as e:
        logger.error(f"Media Publish Failed: {e}")
        return {
            "status": False,
            "message": str(e)
        }
