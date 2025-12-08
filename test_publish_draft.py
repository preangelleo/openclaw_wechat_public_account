import requests
import os
import json

# Configuration
API_URL = "https://animagent.ai/api/weixin-publish/publish"
# Using the admin key we saw in DEPLOYMENT.md / knew from previous context
# In a real scenario, we should load this from .env, but for this quick test script:
ADMIN_API_KEY = "ag_system_8a3758167e696250ebf7f3d5ae23c8c1ab8c7a5fe3571032c14d77de2b4e25b1"

# Sample Data
article_title = "Test Article 001: Automated Deployment"
article_content = """
# Hello World

This is a **test draft** published via the Animagent WeChat Publisher API.

## Features
- Automated publishing
- Markdown support
- Image handling

![Placekitten](image_1)

End of test.
"""

payload = {
    "title": article_title,
    "author": "Animagent Bot",
    "digest": "This is a test digest for the API verification.",
    "article_markdown": article_content,
    "images_list": [
        {
            "image_index": 1,
            "image_type": "url",
            "image_url": "https://www.google.com/images/branding/googlelogo/2x/googlelogo_color_272x92dp.png",
            "image_alt": "Google Logo Test"
        }
    ],
    "cover_image_index": 1,
    "auto_publish": False
}

headers = {
    "Content-Type": "application/json",
    "X-Admin-Api-Key": ADMIN_API_KEY
}

print(f"Sending request to {API_URL}...")
try:
    response = requests.post(API_URL, json=payload, headers=headers)
    
    print(f"Status Code: {response.status_code}")
    try:
        data = response.json()
        print("Response JSON:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        if response.status_code == 200 and data.get("status") == True:
            print("\n✅ SUCCESS: Draft created successfully!")
        else:
            print("\n❌ FAILURE: API returned error.")
            
    except json.JSONDecodeError:
        print("Response Body (Not JSON):")
        print(response.text)

except Exception as e:
    print(f"Error: {e}")
