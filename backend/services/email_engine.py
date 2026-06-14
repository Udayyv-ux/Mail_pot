"""
Email Engine logic — handles template rendering and SMTP sending.
"""
import asyncio
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import aiosmtplib
from groq import Groq
import json
from bs4 import BeautifulSoup
import httpx

from backend.config import settings
from backend.database import SessionLocal
from backend.models.client import Client
from backend.models.template import Template
from backend.models.email_log import EmailLog
from backend.utils.encryption import decrypt_value

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

async def send_template_email(to_email: str, first_name: str, template, smtp_config: dict) -> tuple[bool, str]:
    """Send an HTML email using the provided template and SMTP config."""
    if not first_name or not first_name.strip():
        first_name = "There"
        
    subject = template.subject
    html_body = template.body_html.replace("{first_name}", first_name)
    
    if getattr(template, 'banner_url', None):
        html_body = f'<img src="{template.banner_url}" style="max-width:100%;"><br><br>' + html_body
    
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
    
    ports_to_try = []
    if smtp_port:
        ports_to_try.append(int(smtp_port))
    for p in [465, 587, 25]:
        if p not in ports_to_try:
            ports_to_try.append(p)
            
    last_error = ""
    for port in ports_to_try:
        try:
            use_tls = (port == 465)
            start_tls = (port == 587 or port == 25)
            
            await aiosmtplib.send(
                msg,
                hostname=smtp_host,
                port=port,
                use_tls=use_tls,
                start_tls=start_tls,
                username=smtp_email,
                password=smtp_password
            )
            return True, ""
        except Exception as e:
            last_error = f"Port {port}: {str(e)}"
            continue
            
    return False, f"All ports failed. Last error: {last_error}"

async def run_blast_engine(client_id: str, batch_size: int, delay_seconds: int):
    from sqlalchemy import select
    
    async with SessionLocal() as db:
        client = await db.get(Client, client_id)
        if not client or not client.google_sheet_id:
            return
            
        templates_res = await db.execute(select(Template).where(Template.client_id == client_id, Template.is_active == True))
        templates = templates_res.scalars().all()
        if not templates:
            return
            
        smtp_config = {
            "email": client.smtp_email,
            "password": decrypt_value(client.smtp_password_enc) if client.smtp_password_enc else None,
            "host": client.smtp_host,
            "port": client.smtp_port
        }
        groq_key = decrypt_value(client.groq_api_key_enc) if client.groq_api_key_enc else None

    from backend.services.sheets_service import get_sheet_data, update_sheet_cell
    try:
        _, rows = await get_sheet_data(client.google_sheet_id)
    except Exception as e:
        print(f"Failed to fetch sheet: {e}")
        return
        
    sent_in_batch = 0
    
    for i, row in enumerate(rows):
        if i == 0: continue # Header
        if len(row) < 3: continue
        name = row[0]
        email = row[1]
        inquiry = row[2]
        status = row[4] if len(row) > 4 else ""
        if status == "Sent": continue
        
        category = categorize_with_ai(inquiry, templates, groq_key)
        
        target_template = next((t for t in templates if t.project_name == category), None)
        if not target_template:
            target_template = templates[0]
            
        success, err = await send_template_email(email, name, target_template, smtp_config)
        status_str = "sent" if success else "failed"
        
        async with SessionLocal() as db:
            log = EmailLog(
                client_id=client_id,
                recipient_email=email,
                recipient_name=name,
                template_used=target_template.project_name,
                category_assigned=category,
                status=status_str,
                error_message=err if not success else "",
                sent_at=datetime.now(timezone.utc) if success else None
            )
            db.add(log)
            await db.commit()
            
        try:
            await update_sheet_cell(client.google_sheet_id, i+1, 4, category)
            await asyncio.sleep(1)
            await update_sheet_cell(client.google_sheet_id, i+1, 5, "Sent" if success else "Failed")
        except:
            pass
            
        sent_in_batch += 1
        if sent_in_batch >= batch_size:
            sent_in_batch = 0
            await asyncio.sleep(delay_seconds)

