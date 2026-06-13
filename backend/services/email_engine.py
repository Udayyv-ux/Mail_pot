"""
Email Engine logic — handles template rendering and SMTP sending.
"""
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import aiosmtplib
from groq import Groq
import json
from bs4 import BeautifulSoup
import httpx

from backend.config import settings

def categorize_with_ai(lead_info: str, templates: list, groq_key: str) -> str:
    """Use Groq AI to categorize a lead into one of the available templates."""
    if not lead_info or not templates:
        return "General"
    
    categories = [t.project_name for t in templates if t.is_active]
    if not categories:
        return "General"
        
    categories_str = ", ".join([f"'{c}'" for c in categories])
    
    prompt = f"""
    You are an advanced real-estate routing agent. 
    Customer Inquiry: "{lead_info}"
    Available Project IDs: {categories_str}
    
    Instructions: Match the location or intent to the closest Project ID. If unsure, reply 'General'.
    Reply ONLY with the exact matching Project ID string.
    """
    
    try:
        api_key = groq_key if groq_key else settings.GROQ_API_KEY
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        decision = response.choices[0].message.content.strip()
        if decision in categories:
            return decision
        return "General"
    except Exception as e:
        print(f"AI Agent Error: {e}")
        return "General"

async def send_template_email(to_email: str, first_name: str, template, smtp_config: dict) -> bool:
    """Send an HTML email using the provided template and SMTP config."""
    if not first_name or not first_name.strip():
        first_name = "There"
        
    subject = template.subject
    html_body = template.body_html.replace("{first_name}", first_name)
    
    msg = MIMEMultipart('related')
    
    smtp_email = smtp_config.get("email") or settings.DEFAULT_SMTP_EMAIL
    smtp_password = smtp_config.get("password") or settings.DEFAULT_SMTP_PASSWORD
    smtp_host = smtp_config.get("host") or "smtp.gmail.com"
    smtp_port = smtp_config.get("port") or 587
    
    msg['From'] = smtp_email
    msg['To'] = to_email
    msg['Subject'] = subject
    
    msg_alternative = MIMEMultipart('alternative')
    msg.attach(msg_alternative)
    msg_alternative.attach(MIMEText(html_body, 'html'))
    
    # Process images if needed (not fully robust but handles basic cases)
    image_urls = json.loads(template.image_urls_json) if template.image_urls_json else []
    
    try:
        await aiosmtplib.send(
            msg,
            hostname=smtp_host,
            port=smtp_port,
            start_tls=True,
            username=smtp_email,
            password=smtp_password
        )
        return True
    except Exception as e:
        print(f"Email Error to {to_email}: {e}")
        return False
