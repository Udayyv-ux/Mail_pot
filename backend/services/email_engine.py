"""
Autonomous 24/7 Engine — Handles Google Sheets polling, AI categorization, and HTTP Email Blasting.
"""
import asyncio
from datetime import datetime, timezone
import httpx
from groq import Groq
from sqlalchemy import select

from backend.config import settings
from backend.database import SessionLocal
from backend.models.client import Client
from backend.models.template import Template
from backend.models.email_log import EmailLog
from backend.models.app_settings import AppSetting
from backend.services.sheets_service import get_sheet_data, update_sheet_cell

def get_col_index(headers: list, target_name: str) -> int:
    for i, h in enumerate(headers):
        if h.strip().lower() == target_name.strip().lower():
            return i
    return -1

async def get_global_settings(db) -> dict:
    res = await db.execute(select(AppSetting))
    settings_db = res.scalars().all()
    return {s.key: s.value for s in settings_db}

def categorize_with_ai(lead_info: str, templates: list, groq_key: str) -> str:
    """Use Groq AI to categorize a lead into one of the available templates."""
    if not lead_info or not templates:
        return "General"
    categories = [t.project_name for t in templates if t.is_active]
    if not categories:
        return "General"
    
    categories_str = ", ".join([f"'{c}'" for c in categories])
    prompt = f"Customer Inquiry: '{lead_info}'. Match intent to closest Project ID: {categories_str}. Reply ONLY with Project ID."
    
    try:
        api_key = groq_key if groq_key else settings.GROQ_API_KEY
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        decision = response.choices[0].message.content.strip()
        print(f"🤖 AI Categorized '{lead_info}' -> '{decision}'")
        return decision if decision in categories else categories[0]
    except Exception as e:
        print(f"AI Categorization Error: {e}")
        return categories[0]

async def send_email_via_resend(to_email: str, first_name: str, template, client_email: str, api_key: str, global_sender: str) -> tuple[bool, str]:
    if not api_key:
        return False, "Global Resend API key is missing. Admin must configure it."
    
    subject = template.subject
    html_body = template.body_html.replace("{first_name}", first_name or "There")
    if getattr(template, 'banner_url', None):
        html_body = f'<img src="{template.banner_url}" style="max-width:100%;"><br><br>' + html_body

    payload = {
        "from": global_sender or "hello@example.com",
        "to": [to_email],
        "reply_to": client_email,
        "subject": subject,
        "html": html_body
    }

    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
                timeout=15.0
            )
            if resp.status_code in [200, 201]:
                return True, ""
            return False, f"Resend API Error: {resp.text}"
    except Exception as e:
        return False, f"HTTP Error: {str(e)}"

async def run_247_engine():
    """Background loop that polls all clients every 60 seconds."""
    print("🚀 24/7 Autonomous Engine Started...")
    while True:
        try:
            async with SessionLocal() as db:
                clients_res = await db.execute(select(Client).where(Client.status == "active", Client.google_sheet_id.isnot(None)))
                clients = clients_res.scalars().all()
                global_settings = await get_global_settings(db)
                
            groq_key = global_settings.get("GROQ_API_KEY", settings.GROQ_API_KEY)
            resend_key = global_settings.get("RESEND_API_KEY", "")
            global_sender = global_settings.get("SENDER_EMAIL", "hello@example.com")
            
            for client in clients:
                if client.emails_sent_today >= client.daily_email_limit:
                    print(f"⚠️ Skipping client {client.id} - Daily limit reached ({client.emails_sent_today}/{client.daily_email_limit})")
                    continue # Rate limited
                    
                async with SessionLocal() as db:
                    templates_res = await db.execute(select(Template).where(Template.client_id == client.id, Template.is_active == True))
                    templates = templates_res.scalars().all()
                    # Need client email for Reply-To
                    db_client = await db.get(Client, client.id)
                    await db.refresh(db_client, ['user'])
                    client_email = db_client.user.email if db_client.user else "reply@example.com"
                
                if not templates: continue
                
                try:
                    print(f"🔍 Scanning Google Sheet for Client {client.id}...")
                    _, rows = await get_sheet_data(client.google_sheet_id)
                except Exception as e:
                    print(f"❌ Failed to read sheet for Client {client.id}: {e}")
                    continue # Skip if sheet fails
                    
                if not rows or len(rows) < 2: 
                    print(f"ℹ️ No leads found in sheet for Client {client.id}")
                    continue
                
                headers = rows[0]
                target_cols = [c.strip() for c in (client.target_columns or "Name, Email, Inquiry").split(',')]
                status_col_name = client.status_column or "Status"
                
                name_idx = get_col_index(headers, target_cols[0] if len(target_cols)>0 else "Name")
                email_idx = get_col_index(headers, target_cols[1] if len(target_cols)>1 else "Email")
                inquiry_idx = get_col_index(headers, target_cols[2] if len(target_cols)>2 else "Inquiry")
                status_idx = get_col_index(headers, status_col_name)
                
                if email_idx == -1 or status_idx == -1:
                    continue # Cannot process without email and status column
                    
                for i, row in enumerate(rows[1:], start=1):
                    # Pad row if short
                    while len(row) <= max(name_idx, email_idx, inquiry_idx, status_idx):
                        row.append("")
                        
                    email = row[email_idx]
                    status = row[status_idx]
                    
                    if status.strip().lower() in ["sent", "failed"]:
                        continue # Already processed
                    if not email or "@" not in email:
                        continue
                        
                    name = row[name_idx] if name_idx != -1 else ""
                    inquiry = row[inquiry_idx] if inquiry_idx != -1 else ""
                    
                    print(f"📩 Found new lead: {email} | Status: {status}")
                    
                    category = categorize_with_ai(inquiry, templates, groq_key)
                    target_template = next((t for t in templates if t.project_name == category), templates[0])
                    
                    print(f"📤 Sending '{target_template.project_name}' email to {email} via Resend...")
                    success, err = await send_email_via_resend(email, name, target_template, client_email, resend_key, global_sender)
                    
                    if success:
                        print(f"✅ Successfully sent to {email}")
                    else:
                        print(f"❌ Failed to send to {email}: {err}")
                    
                    # Log to DB
                    async with SessionLocal() as db:
                        log = EmailLog(
                            client_id=client.id,
                            recipient_email=email,
                            recipient_name=name,
                            template_used=target_template.project_name,
                            category_assigned=category,
                            status="sent" if success else "failed",
                            error_message=err,
                            sent_at=datetime.now(timezone.utc) if success else None
                        )
                        db.add(log)
                        if success:
                            db_client = await db.get(Client, client.id)
                            db_client.emails_sent_today += 1
                        await db.commit()
                        
                    # Write to Sheet
                    try:
                        await update_sheet_cell(client.google_sheet_id, i+1, status_idx, "Sent" if success else "Failed")
                        if success:
                            await asyncio.sleep(1) # Delay between sends
                    except:
                        pass
        except Exception as e:
            print(f"24/7 Engine Iteration Error: {e}")
            
        await asyncio.sleep(60) # Poll every minute


