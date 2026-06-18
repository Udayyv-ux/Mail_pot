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
    
    system_prompt = (
        "You are an exact categorization bot. "
        f"You must choose EXACTLY ONE category from this list: {categories_str}. "
        "Do not wrap it in quotes. Do not add any prefix. Respond with the exact name only."
    )
    prompt = f"Customer Inquiry: '{lead_info}'\n\nWhich category does this fit best? Output ONLY the category name."
    
    try:
        api_key = groq_key if groq_key else settings.GROQ_API_KEY
        client = Groq(api_key=api_key)
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.1-8b-instant",
        )
        decision = response.choices[0].message.content.strip()
        # Clean quotes if AI added them
        decision = decision.strip("'").strip('"')
        
        print(f"🤖 AI Categorized '{lead_info}' -> '{decision}'")
        
        # Exact match
        if decision in categories:
            return decision
            
        # Fuzzy fallback match
        for c in categories:
            if c.lower() in decision.lower():
                return c
                
        return categories[0]
    except Exception as e:
        print(f"AI Categorization Error: {e}")
        return categories[0]

import base64
from email.message import EmailMessage

async def refresh_google_token(user, db) -> str | None:
    if not user.google_refresh_token:
        return user.google_access_token
        
    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "refresh_token": user.google_refresh_token,
                    "grant_type": "refresh_token"
                },
                timeout=10.0
            )
            if resp.status_code == 200:
                data = resp.json()
                new_access_token = data.get("access_token")
                if new_access_token:
                    user.google_access_token = new_access_token
                    await db.commit()
                    return new_access_token
            return user.google_access_token
    except Exception as e:
        print(f"Token refresh failed: {e}")
        return user.google_access_token

async def send_email_via_gmail_api(to_email: str, first_name: str, template, access_token: str) -> tuple[bool, str]:
    if not access_token:
        return False, "Client user has not authenticated with Google or access token is missing."
    
    subject = template.subject
    html_body = template.body_html.replace("{first_name}", first_name or "There")
    if getattr(template, 'banner_url', None):
        banner_url = template.banner_url
        if banner_url.startswith("/"):
            banner_url = settings.APP_URL.rstrip('/') + banner_url
        html_body = f'<img src="{banner_url}" style="max-width:100%;"><br><br>' + html_body

    msg = EmailMessage()
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.set_content("Please view this email in an HTML-compatible client.")
    msg.add_alternative(html_body, subtype='html')
    
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
    payload = {"raw": raw}

    try:
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                json=payload,
                timeout=15.0
            )
            if resp.status_code == 200:
                return True, ""
            elif resp.status_code == 401:
                return False, "Gmail API Unauthorized. Token may be expired or revoked."
            return False, f"Gmail API Error: {resp.text}"
    except Exception as e:
        return False, f"HTTP Error: {str(e)}"

async def run_247_engine():
    """Background loop that polls all campaigns every 60 seconds."""
    print("🚀 24/7 Autonomous Engine Started...")
    while True:
        try:
            async with SessionLocal() as db:
                from backend.models.campaign import Campaign
                campaigns_res = await db.execute(select(Campaign).where(Campaign.is_active == True))
                campaigns = campaigns_res.scalars().all()
                global_settings = await get_global_settings(db)
                
            groq_key = global_settings.get("GROQ_API_KEY", settings.GROQ_API_KEY)
            
            for campaign in campaigns:
                async with SessionLocal() as db:
                    db_client = await db.get(Client, campaign.client_id)
                    if not db_client or db_client.status != "active":
                        continue
                        
                    if db_client.emails_sent_today >= db_client.daily_email_limit:
                        print(f"⚠️ Skipping campaign {campaign.id} - Client daily limit reached ({db_client.emails_sent_today}/{db_client.daily_email_limit})")
                        continue
                        
                    templates_res = await db.execute(select(Template).where(Template.client_id == campaign.client_id, Template.is_active == True))
                    templates = templates_res.scalars().all()
                    
                    await db.refresh(db_client, ['user'])
                    client_user = db_client.user
                    
                    access_token = None
                    if client_user:
                        access_token = await refresh_google_token(client_user, db)
                
                if not templates: continue
                
                try:
                    print(f"🔍 Scanning Google Sheet for Campaign '{campaign.name}'...")
                    _, rows = await get_sheet_data(campaign.google_sheet_id)
                except Exception as e:
                    print(f"❌ Failed to read sheet for Campaign {campaign.id}: {e}")
                    continue
                    
                if not rows or len(rows) < 2: 
                    continue
                
                headers = rows[0]
                target_cols = [c.strip() for c in (campaign.target_columns or "Name, Email, Inquiry").split(',')]
                status_col_name = campaign.status_column or "Status"
                
                name_idx = get_col_index(headers, target_cols[0] if len(target_cols)>0 else "Name")
                email_idx = get_col_index(headers, target_cols[1] if len(target_cols)>1 else "Email")
                inquiry_idx = get_col_index(headers, target_cols[2] if len(target_cols)>2 else "Inquiry")
                status_idx = get_col_index(headers, status_col_name)
                
                if email_idx == -1 or status_idx == -1:
                    continue
                    
                for i, row in enumerate(rows[1:], start=1):
                    while len(row) <= max(name_idx, email_idx, inquiry_idx, status_idx):
                        row.append("")
                        
                    email = row[email_idx]
                    status = row[status_idx]
                    
                    if not email or "@" not in email:
                        continue
                        
                    name = row[name_idx] if name_idx != -1 else ""
                    inquiry = row[inquiry_idx] if inquiry_idx != -1 else ""
                    
                    target_template = None
                    category = "General"
                    is_follow_up_run = False
                    
                    # 1. Check if it needs a follow-up
                    if status.strip().lower() == "sent" and campaign.follow_up_days > 0 and campaign.follow_up_template_id:
                        async with SessionLocal() as db:
                            res = await db.execute(select(EmailLog).where(
                                EmailLog.campaign_id == campaign.id,
                                EmailLog.recipient_email == email,
                                EmailLog.is_follow_up == False,
                                EmailLog.status == "sent"
                            ).order_by(EmailLog.sent_at.desc()))
                            last_log = res.scalars().first()
                            
                            if last_log and last_log.sent_at:
                                days_since = (datetime.now(timezone.utc) - last_log.sent_at).days
                                if days_since >= campaign.follow_up_days:
                                    target_template = await db.get(Template, campaign.follow_up_template_id)
                                    is_follow_up_run = True
                                    category = "FollowUp"

                    # 2. Check if it's a new lead
                    elif status.strip() == "":
                        print(f"📩 Found new lead: {email}")
                        category = categorize_with_ai(inquiry, templates, groq_key)
                        target_template = next((t for t in templates if t.project_name == category), templates[0])
                    
                    # 3. Send email if a template was selected
                    if target_template:
                        print(f"📤 Sending '{target_template.project_name}' email to {email}...")
                        success, err = await send_email_via_gmail_api(email, name, target_template, access_token)
                        
                        if success:
                            print(f"✅ Successfully sent to {email}")
                        else:
                            print(f"❌ Failed to send to {email}: {err}")
                        
                        # Log to DB
                        async with SessionLocal() as db:
                            log = EmailLog(
                                client_id=campaign.client_id,
                                campaign_id=campaign.id,
                                recipient_email=email,
                                recipient_name=name,
                                template_used=target_template.project_name,
                                category_assigned=category,
                                status="sent" if success else "failed",
                                error_message=err,
                                sent_at=datetime.now(timezone.utc) if success else None,
                                is_follow_up=is_follow_up_run
                            )
                            db.add(log)
                            if success:
                                db_client = await db.get(Client, campaign.client_id)
                                db_client.emails_sent_today += 1
                            await db.commit()
                            
                        # Write to Sheet
                        try:
                            new_status = "Followed Up" if is_follow_up_run else "Sent"
                            if not success: new_status = "Failed"
                            print(f"📝 Updating sheet row {i+1}, col {status_idx + 1} to '{new_status}'")
                            await update_sheet_cell(campaign.google_sheet_id, i+1, status_idx + 1, new_status)
                            if success:
                                await asyncio.sleep(1) # Delay between sends
                        except Exception as e:
                            print(f"❌ Failed to update sheet: {e}")
                            
        except Exception as e:
            print(f"24/7 Engine Iteration Error: {e}")
            
        await asyncio.sleep(60) # Poll every minute


