import json
import logging
import logging
import httpx
from typing import Dict, List, Any
from .config import OPENROUTER_API_KEY, OPENROUTER_HEADER_SITE_URL, OPENROUTER_HEADER_SITE_NAME, TEXT_MODEL_LITE

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self, model=TEXT_MODEL_LITE):
        self.model = model
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": OPENROUTER_HEADER_SITE_URL,
            "X-Title": OPENROUTER_HEADER_SITE_NAME,
            "Content-Type": "application/json"
        }

    async def process_article_content(self, article_markdown: str) -> List[Dict[str, Any]]:
        """
        Converts Markdown content into a structured JSON suitable for WeChat rendering.
        """
        # Define JSON Schema for the structured output as requested
        json_schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["header", "paragraph", "image", "list", "quote", "table", "code"]},
                    "index": {"type": "integer"}, # Just for ordering or referencing
                    "content": {"type": "string"},
                    "level": {"type": "integer"}, # For headers
                    "style": {"type": "string"} # Optional custom style hints
                },
                "required": ["type", "content"]
            }
        }

        system_prompt = """
        You are an expert WeChat Official Account editor.
        Your task is to convert the provided Markdown article into a structured JSON format that can be easily rendered into WeChat-compatible HTML. Do not concise, brievy or omit any content.
        
        Rules:
        1. Parse Headers (h1, h2, h3) -> type: "header", level: 1/2/3.
        2. Parse Paragraphs -> type: "paragraph".
        3. Parse Images encoded as `image_{index}`:
           - CRITICAL: Images MUST be extracted as their own individual JSON objects with type="image".
           - CRITICAL: Do NOT leave "image_{index}" inside a paragraph content string. Break the paragraph before and after the image.
           - Example: "Text... image_1 ...Text" -> Paragraph("Text..."), Image(index=1), Paragraph("...Text").
        4. Parse Lists -> type: "list", content: inner HTML `<ul>/<li>` string. IMPORTANT: Do not include newlines between `<li>` tags. Output compact HTML.
        5. Parse Blockquotes -> type: "quote".
        6. Parse Tables -> type: "table", content: valid HTML `<table>` string with simple inline styles (border, padding).
        7. Keep the content clean. Remove markdown symbols like ## or ** in the content field, apply them as structural meaning.
        8. For "image_{index}", set the 'index' field to the integer N.
        """

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": article_markdown}
            ],

            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "wechat_article_structure",
                    "strict": True,
                    "schema": json_schema
                }
            },
            "include_reasoning": False
        }

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.api_url, headers=self.headers, json=payload, timeout=120)
            response.raise_for_status()
            result = response.json()
            
            content_str = result['choices'][0]['message']['content']
            
            # The structure should be a list of objects
            parsed_content = json.loads(content_str)
            return parsed_content
            
        except Exception as e:
            logger.error(f"LLM Processing Failed: {e}")
            # Fallback: Return a simple structure if LLM fails? Or raise.
            raise


    async def get_chat_response(self, user_message: str) -> str:
        """
        Standard chat capability using OpenRouter.
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a helpful assistant for the Animagent WeChat Account. Please keep your reply concise and under 500 characters."},
                {"role": "user", "content": user_message}
            ]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.api_url, headers=self.headers, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # Enforce WeChat Passive Reply Limit (~600 chars)
            if len(content) > 600:
                logger.warning(f"Response too long ({len(content)}), truncating to 600.")
                content = content[:597] + "..."
                
            return content
        except Exception as e:
            logger.error(f"Chat Generaton Failed: {e}")
            return "对不起，我现在有点繁忙，请稍后再试。"

llm_client = LLMClient()
