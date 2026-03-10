import logging
import requests
import json
import time
import re
from .token_manager import token_manager
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class DraftManager:
    def __init__(self):
        # Found via inspection of user-edited draft (2025-12-24)
        self.WECHAT_ACCOUNT_BIZ = "MjM5MzM4MzQwMw==" 
        self.WECHAT_ACCOUNT_ALIAS = "wanglijie1979"
        self.WECHAT_ACCOUNT_NICKNAME = "王利杰"
        self.WECHAT_HEAD_IMG = "http://mmbiz.qpic.cn/mmbiz_png/icktoa6sia2tnWTJ5hrdZ3NTORibqNGvdkEydX2hBKpicVzmSauJriaF7AS5CMoicMzibn0RYWzaV9tiagXIC3lTvHIPtQ/0?wx_fmt=png"
        self.WECHAT_SIGNATURE = "教你解读市场周期、分析宏观数据，做出高胜率的投资决策。我们也会讨论AI、比特币和全球宏观趋势。"

    def _get_account_card_html(self) -> str:
        """
        Generates the HTML for the Official Account Card.
        Uses the exact snippet structure found in a valid WeChat draft.
        """
        if not self.WECHAT_ACCOUNT_BIZ:
            return ""

        # Exact structure extracted from inspection
        card_html = f'''
        <p><br/></p>
        <mp-common-profile 
            class="js_uneditable custom_select_card mp_profile_iframe" 
            data-pluginname="mpprofile" 
            data-nickname="{self.WECHAT_ACCOUNT_NICKNAME}" 
            data-alias="{self.WECHAT_ACCOUNT_ALIAS}" 
            data-from="0" 
            data-headimg="{self.WECHAT_HEAD_IMG}" 
            data-signature="{self.WECHAT_SIGNATURE}" 
            data-id="{self.WECHAT_ACCOUNT_BIZ}" 
            data-is_biz_ban="0" 
            data-service_type="1" 
            data-verify_status="1"
        ></mp-common-profile>
        '''
        return card_html

    def _render_html(self, structured_content: List[Dict[str, Any]], image_url_map: Dict[int, str]) -> str:
        """
        Renders the structured content into WeChat-compatible HTML.
        image_url_map: mapping from integer index to WeChat URL.
        """
        html_parts = []
        
        # Base style wrapper
        html_parts.append('<div style="font-family: -apple-system-font, BlinkMacSystemFont, \'Helvetica Neue\', \'PingFang SC\', \'Hiragino Sans GB\', \'Microsoft YaHei UI\', \'Microsoft YaHei\', Arial, sans-serif; letter-spacing: 0.034em;">')
        
        for i, item in enumerate(structured_content):
            item_type = item.get("type")
            content = item.get("content", "")
            
            # Determine previous item type for transition logic
            prev_type = structured_content[i-1].get("type") if i > 0 else None

            if item_type == "header":
                level = item.get("level", 2)
                font_size = "20px" if level == 1 else "18px"
                
                # Spacing Logic:
                # Add newline if not first item AND previous item was NOT a quote (quotes already add bottom spacing).
                # User reported double spacing when Quote -> Header.
                prefix = ""
                if i > 0 and prev_type != "quote":
                     prefix = "<br/>"
                
                html_parts.append(f'{prefix}<h{level} style="font-size: {font_size}; font-weight: bold; margin-top: 20px; margin-bottom: 10px;">{content}</h{level}>')
                
            elif item_type == "paragraph":
                if not content or not content.strip():
                    html_parts.append('<br/>')
                else:
                    # Apply inline formatting
                    fmt_content = self._parse_inline_formatting(content)
                    html_parts.append(f'<p style="font-size: 16px; line-height: 1.6; margin-bottom: 10px; text-align: justify;">{fmt_content}</p>')
                    
            elif item_type == "image":
                # ... (Image Logic) ...
                image_idx = item.get("index")
                if image_idx is None and content.startswith("image_"):
                    try:
                        image_idx = int(content.split("_")[1])
                    except:
                        pass
                
                if image_idx is not None and image_idx in image_url_map:
                    img_url = image_url_map[image_idx]
                    html_parts.append(f'<p style="text-align: center; margin-top: 10px; margin-bottom: 10px;"><img src="{img_url}" style="width: 100%; height: auto; border-radius: 4px;" /></p>')
                else:
                    html_parts.append(f'<p style="color: red;">[Missing Image: {content}]</p>')
            
            elif item_type == "quote":
                # Quote has dedicated spacing around it.
                html_parts.append('<br/>') 
                fmt_content = self._parse_inline_formatting(content)
                html_parts.append(f'<blockquote style="padding-left: 10px; border-left: 3px solid #dbdbdb; color: #666; font-size: 15px; margin: 10px 0;">{fmt_content}</blockquote>')
                html_parts.append('<br/>')
                
            elif item_type == "list":
                # Fix List Styling:
                # 1. Detect if Ordered (<ol>) or Unordered (<ul>)
                # 2. Inject explicit list-style-type and padding.
                clean_content = content.replace("\n\n", "").replace("\n", "")
                
                # Assume LLM sends <ul> or <ol>. We inject style into the tag.
                # Regex or string replace is safer than parsing.
                if "<ol" in clean_content:
                    clean_content = clean_content.replace("<ol", '<ol style="list-style-type: decimal; margin-left: 20px; padding-left: 20px;"')
                elif "<ul" in clean_content:
                    clean_content = clean_content.replace("<ul", '<ul style="list-style-type: disc; margin-left: 20px; padding-left: 20px;"')
                
                # Apply formatting to list content - wait, LIST content from LLM is ALREADY HTML <ul><li>...</li></ul>
                # So we can't just run regex on the whole block indiscriminately if it contains tags?
                # The regex \*\*(.+?)\*\* should be safe even if tags exist, as long as ** isn't inside attributes.
                # But wait, LLM returns "content": "<ul><li>Item 1</li></ul>"
                # If LLM returns "<ul><li>**Bold**</li></ul>", the regex will find **Bold** and replace it.
                # So it IS safe to run it on clean_content.
                
                fmt_content = self._parse_inline_formatting(clean_content)
                html_parts.append(f'<div style="margin: 10px 0; font-size: 16px;">{fmt_content}</div>')

            elif item_type == "table":
                 html_parts.append(f'<div style="margin: 20px 0; overflow-x: auto;">{content}</div>')

            elif item_type == "video":
                 # Video Embedding
                 # Ideally, we need a media_id or a vid.
                 # If content is a URL or media_id, we can try to render.
                 # For now, just a placeholder or link.
                 if content.startswith("http"):
                     html_parts.append(f'<p style="text-align: center;"><a href="{content}">Watch Video</a></p>')
                 else:
                     html_parts.append(f'<p style="text-align: center; color: #888;">[Video: {content}]</p>')
        
        html_parts.append('</div>')
        return "".join(html_parts)

    def _parse_inline_formatting(self, text: str) -> str:
        """
        Parses inline markdown formatting.
        Currently supports:
        - **bold** -> <strong>bold</strong>
        """
        # Replace **text** with <strong>text</strong>
        # Non-greedy match for content inside stars
        # Note: We need to make sure we don't break existing HTML tags if text contains them
        return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)

    def create_draft(self, appid: str, secret: str, title: str, author: str, digest: str, content_html: str, thumb_media_id: str, content_source_url: str = "", audio_media_id: str = None, redis_url: str = None) -> str:
        """
        Submits the draft to WeChat. Returns media_id of the draft.
        """
        token = token_manager.get_token(appid, secret, redis_url)
        url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"
        
        # Insert Audio if present
        final_content = content_html
        if audio_media_id:
             # WeChat <mpvoice> tag format
             # Must be at the beginning? User said "插到文章的一开头"
             audio_tag = f'<p><mpvoice voice_encode_fileid="{audio_media_id}" class="js_editor_audio audio_iframe"></mpvoice></p>'
             final_content = audio_tag + content_html

        # Inject Official Account Card (End of Article)
        account_card_html = self._get_account_card_html()
        if account_card_html:
            final_content = final_content + account_card_html

        article_payload = {
            "title": title,
            "author": author,
            "digest": digest,
            "content": final_content,
            "thumb_media_id": thumb_media_id,
            "show_cover_pic": 1, 
            "need_open_comment": 1, 
            "only_fans_can_comment": 0
        }
        
        if content_source_url:
            article_payload["content_source_url"] = content_source_url

        payload = {
            "articles": [article_payload]
        }
        
        # Use ensure_ascii=False to send raw UTF-8 characters instead of \u escapes
        # This prevents WeChat from rendering literal unicode escapes if their parser is sensitive
        payload_json = json.dumps(payload, ensure_ascii=False).encode('utf-8')
        headers = {'Content-Type': 'application/json; charset=utf-8'}
        
        resp = requests.post(url, data=payload_json, headers=headers, timeout=30)
        data = resp.json()
        
        if "media_id" not in data:
            raise Exception(f"Failed to create draft: {data}")
            
        return data["media_id"]

    def publish_draft(self, appid: str, secret: str, media_id: str, redis_url: str = None) -> str:
        """
        Publishes a draft.
        """
        token = token_manager.get_token(appid, secret, redis_url)
        url = f"https://api.weixin.qq.com/cgi-bin/freepublish/submit?access_token={token}"
        
        payload = {
            "media_id": media_id
        }
        
        response = requests.post(url, json=payload, timeout=30)
        data = response.json()
        
        if data.get("errcode") == 0:
            return data.get("publish_id")
        else:
            raise Exception(f"Failed to publish draft: {data}")

    def get_draft_url(self, appid: str, secret: str, media_id: str, redis_url: str = None) -> str:
        """
        Retrieves the permanent URL of the draft by media_id.
        """
        token = token_manager.get_token(appid, secret, redis_url)
        url = f"https://api.weixin.qq.com/cgi-bin/draft/get?access_token={token}"
        
        # WeChat 'get' API usually takes json={"media_id": ...}
        payload = {"media_id": media_id}
        
        retry_count = 3
        for attempt in range(retry_count):
            try:
                resp = requests.post(url, json=payload, timeout=30)
                data = resp.json()
                
                if "news_item" in data and len(data["news_item"]) > 0:
                    url = data["news_item"][0]["url"]
                    logger.info(f"Draft URL retrieved successfully on attempt {attempt + 1}: {url}")
                    return url
                else:
                    logger.warning(f"Attempt {attempt + 1}/{retry_count}: Could not find URL for draft {media_id}. Resp: {data}")
                    if attempt < retry_count - 1:
                        time.sleep(2)
            except Exception as e:
                logger.error(f"Attempt {attempt + 1}/{retry_count}: Error getting draft URL: {e}")
                if attempt < retry_count - 1:
                    time.sleep(2)
        
        return ""

    def send_preview(self, appid: str, secret: str, media_id: str, wxname: str, redis_url: str = None) -> bool:
        """
        Sends a preview of the draft to a specific WeChat user by their wxname (WeChat ID).
        """
        token = token_manager.get_token(appid, secret, redis_url)
        # Preview API endpoint
        url = f"https://api.weixin.qq.com/cgi-bin/message/mass/preview?access_token={token}"
        
        payload = {
            "towxname": wxname,
            "mpnews": {
                "media_id": media_id
            },
            "msgtype": "mpnews"
        }
        
        # Ensure UTF-8 encoding for payload 
        response = requests.post(url, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'), timeout=30)
        data = response.json()
        
        if data.get("errcode") == 0:
            print(f"Preview sent successfully to {wxname}!")
            return True
        else:
            print(f"Failed to send preview to {wxname}: {data}")
            # Do not raise exception to avoid blocking the main flow, just log and return False
            return False

draft_manager = DraftManager()
