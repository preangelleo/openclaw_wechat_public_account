import json
import logging
import requests
from typing import Dict, List, Any
from .config import OPENROUTER_API_KEY, OPENROUTER_HEADER_SITE_URL, OPENROUTER_HEADER_SITE_NAME

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self, model="google/gemini-2.5-flash"):
        self.model = model
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": OPENROUTER_HEADER_SITE_URL,
            "X-Title": OPENROUTER_HEADER_SITE_NAME,
            "Content-Type": "application/json"
        }

    def process_article_content(self, article_markdown: str) -> List[Dict[str, Any]]:
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
        Your task is to convert the provided Markdown article into a structured JSON format that can be easily rendered into WeChat-compatible HTML.
        
        Rules:
        1. Parse Headers (h1, h2, h3) -> type: "header", level: 1/2/3.
        2. Parse Paragraphs -> type: "paragraph".
        3. Parse Images encoded as `image_{index}` in the text -> type: "image", content: "image_{index}".
        4. Parse Lists -> type: "list", content: inner HTML `<ul>/<li>` string. IMPORTANT: Do not include newlines between `<li>` tags. Output compact HTML.
        5. Parse Blockquotes -> type: "quote".
        6. Parse Tables -> type: "table", content: valid HTML `<table>` string with simple inline styles (border, padding).
        7. Keep the content clean. Remove markdown symbols like ## or ** in the content field, apply them as structural meaning.
        8. For "image_{index}", strictly preserve the exact string "image_{index}" in the content field.
        """

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": article_markdown}
            ],
            # Google Gemini 2.5 Flash on OpenRouter supports structured output via json_schema (or just response_format in some adapters).
            # We will try the standard 'json_object' mode or response_format depending on provider support.
            # OpenRouter's support for 'json_schema' might vary by underlying provider implementation. 
            # safe bet: prompt for JSON and use "response_format": {"type": "json_object"} if supported.
            # The user provided a specific schema-based payload example. We'll follow that.
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
            response = requests.post(self.api_url, headers=self.headers, json=payload, timeout=120)
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

llm_client = LLMClient()
