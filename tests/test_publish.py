import os
import requests
import time
from dotenv import load_dotenv

# Load local .env ONLY for testing. The server should run without it.
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

def test_publish_api():
    url = "http://localhost:5006/publish"
    admin_key = os.getenv("ADMIN_API_KEY")
    
    if not admin_key:
        print("Error: ADMIN_API_KEY missing from .env")
        return

    headers = {
        "X-Admin-Api-Key": admin_key
    }
    
    payload = {
        "publish_type": "article",
        "title": "OpenClaw WeChat Refactor Test",
        "author": "Test Bot",
        "digest": "Testing dynamic credentials injection",
        "cover_image_index": 1,
        "images_list": [
            {
                "image_index": 1,
                "image_type": "url",
                "image_url": "https://picsum.photos/800/600"
            }
        ],
        "article_markdown": "# Test Success\n\nIf you see this, the stateless OpenClaw publisher works! ![Cover](image_1)",
        "use_llm_parser": False,
        "credentials": {
            "wx_appid": os.getenv("APPID"),
            "wx_secret": os.getenv("SECRET"),
            "openrouter_api_key": os.getenv("OPENROUTER_API_KEY")
        }
    }

    print("Sending publish request to local server on port 5006...")
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        try:
            print(f"Response: {response.json()}")
            if response.status_code == 200 and response.json().get("status") == True:
                print("✅ Test Passed: Successfully drafted article statelessly!")
            else:
                print("❌ Test Failed: API returned error.")
        except Exception:
            print(f"Raw Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Test Failed: Could not connect to http://localhost:5006/publish. Is the server running?")

if __name__ == "__main__":
    test_publish_api()
