
import requests
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Environment Configuration
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")
ANIMAGENT_GMAIL_ADDRESS = os.getenv("ANIMAGENT_GMAIL_ADDRESS")
ANIMAGENT_GMAIL_PASSWORD = os.getenv("ANIMAGENT_GMAIL_PASSWORD")
GMAIL_SERVICE_URL = "https://animagent.ai/api/concurrent-gmail/api/v1/send-email"

def send_preview_email(to_address: str, draft_url: str, publish_endpoint: str, article_title: str):
    """
    Sends an HTML email with the Draft Preview Link and a Publish Action Button.
    
    :param to_address: Recipient email
    :param draft_url: The WeChat permanent link to the draft
    :param publish_endpoint: The URL to trigger publication
    :param article_title: The title of the article
    """
    subject = f"WeChat Draft: {article_title}"
    
    # Simple HTML Template
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #07c160;">WeChat Draft Ready</h2>
        <h3 style="color: #333;">{article_title}</h3>
        <p>A new WeChat draft has been created successfully.</p>
        
        <div style="margin: 20px 0; padding: 15px; background-color: #f9f9f9; border-left: 4px solid #07c160;">
            <p><strong>Step 1: Preview</strong></p>
            <p>Check the rendering on your phone or browser:</p>
            <a href="{draft_url}" style="display: inline-block; padding: 10px 20px; background-color: #07c160; color: white; text-decoration: none; border-radius: 5px;">View Draft</a>
        </div>
        
        <div style="margin: 20px 0; padding: 15px; background-color: #fff0f0; border-left: 4px solid #d9534f;">
            <p><strong>Step 2: Approve & Publish</strong></p>
            <p>If the preview looks good, click below to publish immediately:</p>
            <a href="{publish_endpoint}" style="display: inline-block; padding: 10px 20px; background-color: #d9534f; color: white; text-decoration: none; border-radius: 5px;">PUBLISH NOW</a>
        </div>
        
        <p style="font-size: 12px; color: #999;">This email was sent by Animagent WeChat Publisher.</p>
    </body>
    </html>
    """
    
    headers = {
        "Admin-API-Key": ADMIN_API_KEY,
        "Content-Type": "application/json"
    }
    
    payload = {
        "to_addresses": to_address,
        "subject": subject,
        "content": html_content,
        "is_html": True,
        # Gmail Service Credentials (passed to the relay service)
        "gmail_address": ANIMAGENT_GMAIL_ADDRESS,
        "gmail_password": ANIMAGENT_GMAIL_PASSWORD,
        "use_default_credentials": False
    }
    
    try:
        logger.info(f"Sending Email to {to_address}...")
        response = requests.post(GMAIL_SERVICE_URL, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            resp_data = response.json()
            if resp_data.get("success"):
                logger.info("✅ Email sent successfully.")
                return True
            else:
                logger.error(f"❌ Email service returned error: {resp_data}")
        else:
            logger.error(f"❌ Failed to send email. Status: {response.status_code}, Body: {response.text}")
            
    except Exception as e:
        logger.error(f"❌ Exception sending email: {e}")

    return False