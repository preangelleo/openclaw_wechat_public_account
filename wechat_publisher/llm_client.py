import json
import logging
import logging
import httpx
import asyncio
import json
from typing import Dict, List, Any
from .config import OPENROUTER_API_KEY, OPENROUTER_HEADER_SITE_URL, OPENROUTER_HEADER_SITE_NAME, TEXT_MODEL_LITE, TEXT_MODEL_LIST

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
        7. Keep the content clean. Remove markdown symbols like ## for headers, BUT PRESERVE bold syntax (**text**) or convert it to <b>text</b> or <strong>text</strong> so it can be rendered.
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

        max_retries = len(TEXT_MODEL_LIST)
        retry_delay = 1

        for idx, model_name in enumerate(TEXT_MODEL_LIST):
            logger.info(f"Step 2: Structuring Content - Attempt {idx + 1}/{max_retries} using model: {model_name}")
            payload["model"] = model_name
            
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(self.api_url, headers=self.headers, json=payload, timeout=120)
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


    async def get_chat_response(self, user_message: str, history: List[Dict] = None) -> Dict[str, Any]:
        """
        NLU Chat with Structured Output.
        Returns Dict with keys: needs_search (bool), search_keywords (str|None), reply_content (str).
        """
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
        system_prompt = """
        You are 'Animagent Assistant' for Wang Lijie (Leo)'s WeChat Account.
        Your goal is to helpful, concise, and smart.
        
        DECISION LOGIC:
        - Analyze the user's input to determine if they want to READ/FIND articles.
        - If YES: Set 'needs_search' = True and extract the most relevant short keyword.
        - If NO (e.g., 'Hello', 'Who are you', 'Tell me a joke'): Set 'needs_search' = False.
        
        Examples:
        - "Tell me about blockchain" -> needs_search: True, keywords: "blockchain"
        - "Do you have articles on investment?" -> needs_search: True, keywords: "investment"
        - "Hi Leo" -> needs_search: False
        
        OUTPUT RULES:
        - Return pure JSON matching the schema.
        - 'reply_content' must be plain text, no markdown headers/bolding, < 500 chars.
        """
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
            "model": self.model,
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
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(self.api_url, headers=self.headers, json=payload, timeout=15)
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
