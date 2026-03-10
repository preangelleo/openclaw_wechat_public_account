import json
import logging
import os
import httpx
import asyncio
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

# Defaults if not provided
DEFAULT_SITE_URL = "https://animagent.ai"
DEFAULT_SITE_NAME = "Animagent.ai"
DEFAULT_TEXT_MODEL = "google/gemini-2.5-flash"
DEFAULT_TEXT_MODEL_LITE = "google/gemini-2.5-flash-lite"
DEFAULT_TEXT_MODEL_LIST = ["google/gemini-2.5-flash", "google/gemini-3-pro-preview"]


class LLMClient:
    def __init__(self):
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

    def _get_headers(self, api_key: str):
        return {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": DEFAULT_SITE_URL,
            "X-Title": DEFAULT_SITE_NAME,
            "Content-Type": "application/json"
        }

    async def process_article_content(self, article_markdown: str, openrouter_api_key: str, openrouter_text_model: str = None) -> List[Dict[str, Any]]:
        """
        Converts Markdown content into a structured JSON suitable for WeChat rendering.
        """
        if not openrouter_api_key:
            raise ValueError("openrouter_api_key is required for process_article_content")
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
                "required": ["type", "content"],
                "additionalProperties": False
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
        4. Parse Lists -> type: "list" OR "paragraph".
           - WeChat Renders Lists Poorly. AVOID LISTS (<ul>/<li>) if possible.
           - ONLY use type="list" if:
             a) Each list item is very short (< 20 chars).
             b) AND there are NO colons (:) or hyphens (-) inside the list item text (which imply a title/description structure).
           - OTHERWISE (for long items or items with ":"), convert the list into a series of type="paragraph" objects.
             - Example input: "- Title: Description..."
             - Output as paragraphs: Paragraph("Title: Description...")
             - Do NOT split the title and description into separate paragraphs. Keep them together as one paragraph.
           - If using type="list", output content as inner HTML `<ul>/<li>` string.
           - CRITICAL: Keep each list item in a SINGLE `<li>` tag. Do not include newlines between tags.
        5. Parse Blockquotes -> type: "quote".
        6. Parse Tables -> type: "table", content: valid HTML `<table>` string with simple inline styles (border, padding).
        7. Keep the content clean. Remove markdown symbols like ## for headers, BUT PRESERVE bold syntax (**text**) or convert it to <b>text</b> or <strong>text</strong> so it can be rendered.
        8. For "image_{index}", set the 'index' field to the integer N.
        """

        payload = {
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
            }
        }

        models_to_try = [openrouter_text_model] if openrouter_text_model else DEFAULT_TEXT_MODEL_LIST
        max_retries = len(models_to_try)
        retry_delay = 1
        
        headers = self._get_headers(openrouter_api_key)

        for idx, model_name in enumerate(models_to_try):
            logger.info(f"Step 2: Structuring Content - Attempt {idx + 1}/{max_retries} using model: {model_name}")
            payload["model"] = model_name
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(self.api_url, headers=headers, json=payload, timeout=120)
                response.raise_for_status()
                result = response.json()
                
                content_str = result['choices'][0]['message']['content']
                
                # The structure should be a list of objects
                parsed_content = json.loads(content_str)
                return parsed_content
                
            except (httpx.RequestError, httpx.HTTPStatusError, httpx.RemoteProtocolError, json.JSONDecodeError) as e:
                logger.warning(f"LLM Processing Failed with model {model_name}: {e}")
                if idx < max_retries - 1:
                    logger.info(f"Retrying with next model in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error(f"All models failed. Last error: {e}")
                    raise
            except Exception as e:
                logger.error(f"LLM Processing Unexpected Error with model {model_name}: {e}")
                raise


    async def get_chat_response(self, user_message: str, history: List[Dict] = None, openrouter_api_key: str = None, openrouter_text_model: str = None, bot_persona: str = None) -> Dict[str, Any]:
        """
        NLU Chat with Structured Output.
        Returns Dict with keys: needs_search (bool), search_keywords (str|None), reply_content (str).
        """
        if not openrouter_api_key:
             logger.warning("No OpenRouter API key provided, skipping LLM chat call.")
             return {
                "needs_search": False,
                "search_keywords": None,
                "reply_content": "开发者未配置大模型 API Key，当前为离线模式。"
             }
        # 1. JSON Schema for NLU
        json_schema = {
            "type": "object",
            "properties": {
                "needs_search": {
                    "type": "boolean",
                    "description": "True if the user is asking for articles, requesting information that requires a database search, or explicitly asking to 'find/search' something. False for general chat, greetings, or questions about the bot itself."
                },
                "search_keywords": {
                    "type": ["string", "null"],
                    "description": "The specific keywords to search for in the database. Extract the core topic (e.g., 'blockchain' from 'articles about blockchain'). Set to null if needs_search is False."
                },
                "reply_content": {
                    "type": "string",
                    "description": "The concise text reply to the user. If needs_search is True, this message will be shown ONLY if no articles are found. If needs_search is False, this is the main response. Keep it under 500 characters."
                }
            },
            "required": ["needs_search", "search_keywords", "reply_content"],
            "additionalProperties": False
        }

        # 2. Convert History (Gemini Format -> OpenAI Format)
        # History in MemoryManager: {'role': 'model'/'user', 'parts': ['text']}
        # OpenRouter expects: {'role': 'assistant'/'user', 'content': 'text'}
        messages = []
        
        # System Prompt
        persona_context = bot_persona if bot_persona else "You are an AI Assistant for this WeChat Official Account."
        
        system_prompt = f"""
        {persona_context}
        Your goal is to helpful, concise, and smart.
        
        DECISION LOGIC:
        - Analyze the user's input to determine if they want to READ/FIND articles.
        - If YES: Set 'needs_search' = True and extract the most relevant short keyword.
        - If NO (e.g., 'Hello', 'Who are you', 'Tell me a joke'): Set 'needs_search' = False.

        FAQ CONTEXT (Use these points to answer naturally if relevant to the user's query):
        1) 我是搭载在公众服务器上的 AI 助理，由 OpenClaw 开源生态驱动。
        2) 我的文章和内容可能会根据运营者的配置随机发送，具体欢迎订阅。
        
        Examples:
        - "Tell me about blockchain" -> needs_search: True, keywords: "blockchain"
        - "Do you have articles on investment?" -> needs_search: True, keywords: "investment"
        - "Hi" -> needs_search: False
        
        OUTPUT RULES:
        - Return pure JSON matching the schema.
        - 'reply_content' must be plain text, no markdown headers/bolding, < 500 chars.
        """
        
        # Inject Welcome Context (Dynamically read welcome.md)
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            welcome_path = os.path.join(current_dir, "welcome.md")
            if os.path.exists(welcome_path):
                with open(welcome_path, "r", encoding="utf-8") as f:
                    welcome_content = f.read()
                system_prompt += f"\n\nCONTEXT (Welcome Message Info):\n{welcome_content}\nUse this info to answer user questions about contact, other channels, or the bot itself."
        except Exception as e:
            logger.warning(f"Failed to inject welcome context: {e}")
            
        messages.append({"role": "system", "content": system_prompt})
        
        if history:
            for msg in history:
                role = "assistant" if msg.get("role") == "model" else "user"
                # Handle parts list safely
                parts = msg.get("parts", [])
                content = parts[0] if parts else ""
                messages.append({"role": role, "content": content})

        # Current User Message
        messages.append({"role": "user", "content": user_message})

        payload = {
            "model": openrouter_text_model or DEFAULT_TEXT_MODEL_LITE,
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "nlu_search_decision",
                    "strict": True,
                    "schema": json_schema
                }
            }
        }
        
        headers = self._get_headers(openrouter_api_key)
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.api_url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()
            result = response.json()
            content_str = result['choices'][0]['message']['content']
            
            # Parse JSON
            parsed_result = json.loads(content_str)
            return parsed_result
            
        except Exception as e:
            logger.error(f"Chat NLU Failed: {e}")
            # Fallback safe response
            return {
                "needs_search": False,
                "search_keywords": None,
                "reply_content": "对不起，我现在有点繁忙，请稍后再试。"
            }

llm_client = LLMClient()
