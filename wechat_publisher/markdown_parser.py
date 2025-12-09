
import re
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class MarkdownParser:
    def __init__(self):
        pass

    def parse_content(self, text: str) -> List[Dict[str, Any]]:
        """
        Parses markdown text into structured content.
        Uses robust regex to find image patterns like:
        - ![alt](image_1)
        - ![alt]([Missing Image: image_1])
        - image_1 
        """
        structured_content = []
        
        # Split text by identifying image patterns. 
        # We capture the image index and the full matching string.
        # Pattern components:
        # 1. Standard/Extracted Markdown Image: !\[.*?\]\(.*?image_(\d+).*?\)
        # 2. Standalone Placeholder: image_(\d+)
        
        # We use a pattern that finds the image index (\d+) embedded in various contexts
        # strict_pattern finds explicit image syntaxes.
        # \!\[.*?\]\([^\)]*?image_(\d+)[^\)]*?\)  matches ![...](...image_1...)
        
        # Let's try a split strategy that isolates the image token.
        
        # Improved Regex:
        # Matches: ![Alt](...image_1...) OR [Missing Image: image_1] OR image_1
        # The goal is to extract '1' and treat the Whole Match as the delimiter to remove.
        
        # Pattern explanation:
        # We need to handle nested structures and prioritizing longest match.
        # 1. Nested Wrapper: [Missing Image: ![...](...image_N...) ] (User's case)
        # 2. Link Wrapper: ![...]( [Missing Image: image_N] ) (User's case)
        # 3. Standard Markdown: ![...](...image_N...)
        # 4. Bracket Wrapper: [Missing Image: image_N]
        # 5. Simple: image_N
        
        # Regex components:
        # A. `!\[.*?\]\(.*?image_(\d+).*?\)`  -> Standard/Link
        # B. `\[Missing Image: .*?image_(\d+).*?\]` -> Bracket Wrapper (Generic '.*?') 
        # But '.*?' inside might match too much if not careful.
        # Let's use `\[Missing Image: (?:(?!\]).)*?image_(\d+).*?\]` to stay inside brackets?
        # Actually, simpler is:
        
        # Priority 1: Nested Wrapper [Missing Image: ![...](...image_N...) ]
        # regex: \[Missing Image:\s*!\[.*?\]\(.*?image_(\d+).*?\)\s*\]
        
        # Priority 2: Bracket Wrapper [Missing Image: image_N] or similar
        # regex: \[Missing Image:.*?image_(\d+).*?\]
        
        # Priority 3: Link wrapper around text ![...]( [Missing Image: image_N] )
        # regex: !\[.*?\]\(.*?\[Missing Image: image_(\d+)\].*?\)
        
        # Priority 4: Standard ![...](image_N)
        # regex: !\[.*?\]\(.*?image_(\d+).*?\)
        
        # Priority 5: Simple image_N
        
        # We combine them with | order by specificity.
        
        regex = r"(?:\[Missing Image:\s*!\[.*?\]\(.*?image_(\d+).*?\)\s*\]|!\[.*?\]\(.*?\[Missing Image: image_(\d+)\].*?\)|\[Missing Image:.*?image_(\d+).*?\]|!\[.*?\]\(.*?image_(\d+).*?\)|image_(\d+))"
        
        last_pos = 0
        matches = list(re.finditer(regex, text, re.DOTALL))
        
        for match in matches:
            # Text before the image
            pre_text = text[last_pos:match.start()]
            if pre_text:
                structured_content.extend(self._parse_text_block(pre_text))
                
            # Extract index from whichever group matched
            # Groups are 1..5 corresponding to the alternatives
            idx = next((g for g in match.groups() if g is not None), None)
            
            structured_content.append({
                "type": "image",
                "index": int(idx),
                "content": match.group(0) # Store full raw string for debugging if needed, or just "image_N"
            })
            
            last_pos = match.end()
            
        # Remaining text
        if last_pos < len(text):
            structured_content.extend(self._parse_text_block(text[last_pos:]))
            
        return structured_content

    def _parse_text_block(self, text: str) -> List[Dict[str, Any]]:
        """
        Parses a block of text for headers, lists, quotes, and paragraphs.
        """
        lines = text.split('\n')
        blocks = []
        
        current_list = []
        current_list_type = None # ul or ol
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
                
            # Headers
            if stripped.startswith('#'):
                # Flush list if any
                if current_list:
                    blocks.append(self._finalize_list(current_list, current_list_type))
                    current_list = []
                    current_list_type = None
                    
                level = len(stripped.split(' ')[0])
                # Cap level at 6, verify it is actually # chars
                if level > 6: level = 6
                content = stripped[level:].strip()
                blocks.append({
                    "type": "header",
                    "level": level,
                    "content": content
                })
                continue
            
            # Quotes
            if stripped.startswith('>'):
                # Flush list
                if current_list:
                    blocks.append(self._finalize_list(current_list, current_list_type))
                    current_list = []
                    current_list_type = None
                    
                content = stripped[1:].strip()
                blocks.append({
                    "type": "quote",
                    "content": content
                })
                continue
                
            # Unordered List
            if stripped.startswith('- ') or stripped.startswith('* '):
                if current_list_type == 'ol': # switch list type, flush old
                     blocks.append(self._finalize_list(current_list, current_list_type))
                     current_list = []
                
                current_list_type = 'ul'
                content = stripped[2:].strip()
                current_list.append(content)
                continue
                
            # Ordered List
            # Regex for "1. ", "10. "
            ol_match = re.match(r"^\d+\.\s+(.*)", stripped)
            if ol_match:
                if current_list_type == 'ul':
                     blocks.append(self._finalize_list(current_list, current_list_type))
                     current_list = []
                
                current_list_type = 'ol'
                content = ol_match.group(1)
                current_list.append(content)
                continue
                
            # Regular Paragraph
            # Flush list
            if current_list:
                blocks.append(self._finalize_list(current_list, current_list_type))
                current_list = []
                current_list_type = None
            
            blocks.append({
                "type": "paragraph",
                "content": stripped
            })
            
        # Final flush
        if current_list:
            blocks.append(self._finalize_list(current_list, current_list_type))
            
        return blocks

    def _finalize_list(self, items: List[str], list_type: str) -> Dict[str, Any]:
        """
        Converts list items to HTML string for the 'content' field.
        """
        tag = "ul" if list_type == 'ul' else "ol"
        html_items = "".join([f"<li>{item}</li>" for item in items])
        return {
            "type": "list",
            "content": f"<{tag}>{html_items}</{tag}>"
        }

markdown_parser = MarkdownParser()
