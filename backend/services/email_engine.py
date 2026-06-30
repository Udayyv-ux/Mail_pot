"""
Autonomous 24/7 Engine — Handles Google Sheets polling, AI categorization, and HTTP Email Blasting.
"""
import asyncio
import uuid
from datetime import datetime, timezone
import httpx
from groq import Groq
from sqlalchemy import select, func, update

from backend.config import settings
from backend.database import SessionLocal
from backend.models.client import Client
from backend.models.template import Template
from backend.models.email_log import EmailLog
from backend.models.email_queue import EmailQueue
from backend.models.app_settings import AppSetting
from backend.models.campaign import Campaign
from backend.services.sheets_service import get_sheet_data, update_sheet_cell, update_sheet_cells_batch
from backend.services.whatsapp_service import send_whatsapp_message

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
        f"You must choose EXACTLY ONE category from this exact list: {categories_str}. "
        "Do not wrap it in quotes. Do not add any prefix, suffix, or explanation. "
        "Output ONLY the exact string from the list."
    )
    prompt = f"Customer Inquiry: '{lead_info}'\n\nWhich category does this fit best?"
    
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
        
        print(f"AI Categorized '{lead_info}' -> '{decision}'")
        
        # Exact match
        if decision in categories:
            return decision
            
        # Fuzzy fallback match (check both ways)
        decision_lower = decision.lower()
        for c in categories:
            c_lower = c.lower()
            if c_lower in decision_lower or decision_lower in c_lower:
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
            else:
                print(f"Token refresh failed with {resp.status_code}: {resp.text}")
            return user.google_access_token
    except Exception as e:
        print(f"Token refresh failed: {e}")
        return user.google_access_token

async def send_email_via_gmail_api(to_email: str, first_name: str, template, access_token: str, log_id: str = None) -> tuple[bool, str]:
    if not access_token:
        return False, "Client user has not authenticated with Google or access token is missing."
    
    subject = template.subject
    html_body = template.body_html.replace("{first_name}", first_name or "There")
    if getattr(template, 'banner_url', None):
        banner_url = template.banner_url
        if banner_url.startswith("/"):
            banner_url = settings.APP_URL.rstrip('/') + banner_url
        html_body = f'<img src="{banner_url}" style="max-width:100%;"><br><br>' + html_body

    if log_id:
        tracking_pixel_url = f"{settings.APP_URL.rstrip('/')}/api/public/track/open/{log_id}"
        html_body += f'<img src="{tracking_pixel_url}" width="1" height="1" style="display:none;" />'

    msg = EmailMessage()
    msg['To'] = to_email
    msg['From'] = 'me'
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
                return False, f"Gmail API 401 Unauthorized. Exact response: {resp.text}"
            return False, f"Gmail API Error: {resp.text}"
    except Exception as e:
        return False, f"HTTP Error: {str(e)}"

_running_campaigns = set()

def is_client_allowed(client):
    now = datetime.now(timezone.utc)
    if client.subscription_ends_at and client.subscription_ends_at > now: return True
    if client.trial_ends_at and client.trial_ends_at > now: return True
    return False

async def process_single_campaign(campaign, groq_key):
    """Processes a single campaign. Handles fetching data, AI matching, and sending."""
    try:
        async with SessionLocal() as db:
            db_client = await db.get(Client, campaign.client_id)
            if not db_client or db_client.status != "active":
                return
                
            if not is_client_allowed(db_client):
                print(f"🚫 Skipping campaign {campaign.id} - Trial/Subscription Expired")
                try:
                    await db.refresh(db_client, ['user'])
                    if db_client.user:
                        _, rows = await get_sheet_data(campaign.google_sheet_id)
                        if rows and len(rows) > 1:
                            headers = rows[0]
                            status_col_name = campaign.status_column or "Status"
                            status_idx = get_col_index(headers, status_col_name)
                            for i, row in enumerate(rows):
                                if i == 0: continue
                                status = row[status_idx] if status_idx < len(row) else ""
                                if not status.strip():
                                    await update_sheet_cell(campaign.google_sheet_id, i+1, status_idx + 1, "Plan Expired")
                                    await asyncio.sleep(1) # respect API rate limits
                except Exception as e:
                    print(f"Failed to notify sheet of expiration: {e}")
                return
                
            if db_client.emails_sent_today >= db_client.daily_email_limit:
                print(f"🛑 Skipping campaign {campaign.id} - Client daily limit reached ({db_client.emails_sent_today}/{db_client.daily_email_limit})")
                return
                
            templates_res = await db.execute(select(Template).where(Template.client_id == campaign.client_id, Template.is_active == True))
            templates = templates_res.scalars().all()
            
            await db.refresh(db_client, ['user'])
            client_user = db_client.user
            
            access_token = None
            if client_user:
                access_token = await refresh_google_token(client_user, db)
            if not templates: return
            
            try:
                _, rows = await get_sheet_data(campaign.google_sheet_id)
                async with SessionLocal() as db:
                    db_camp = await db.get(Campaign, campaign.id)
                    if db_camp:
                        db_camp.last_error = None
                    await db.commit()
            except Exception as e:
                print(f"\u274c Failed to read sheet for Campaign {campaign.id}: {e}")
                async with SessionLocal() as db:
                    db_camp = await db.get(Campaign, campaign.id)
                    if db_camp:
                        db_camp.last_error = f"Failed to read sheet: {str(e)}"
                    await db.commit()
                return
                
            if not rows or len(rows) < 2: 
                async with SessionLocal() as db:
                    db_camp = await db.get(Campaign, campaign.id)
                    if db_camp:
                        db_camp.last_error = "Sheet is empty or missing headers."
                    await db.commit()
                return
            
            headers = rows[0]
            status_col_name = campaign.status_column or "Status"
            
            name_idx, email_idx, inquiry_idx, phone_idx = -1, -1, -1, -1
            for i, h in enumerate(headers):
                hl = h.lower().strip()
                if 'email' in hl and email_idx == -1: email_idx = i
                elif 'name' in hl and name_idx == -1: name_idx = i
                elif ('phone' in hl or 'whatsapp' in hl or 'mobile' in hl) and phone_idx == -1: phone_idx = i
                elif ('inquiry' in hl or 'message' in hl or 'notes' in hl) and inquiry_idx == -1: inquiry_idx = i
            
            status_idx = get_col_index(headers, status_col_name)
            print(f"📊 Column indices - Name: {name_idx}, Email: {email_idx}, Inquiry: {inquiry_idx}, Phone: {phone_idx}, Status: {status_idx}")
            
            if email_idx == -1 or status_idx == -1:
                async with SessionLocal() as db:
                    db_camp = await db.get(Campaign, campaign.id)
                    if db_camp:
                        db_camp.last_error = f"Missing Email or {status_col_name} column."
                    await db.commit()
                return
                
            from datetime import timedelta
            current_hour = datetime.now(timezone.utc).hour
            if current_hour < campaign.send_hours_start or current_hour >= campaign.send_hours_end:
                print(f"⏰ Campaign '{campaign.name}' is outside sending hours ({campaign.send_hours_start}:00 - {campaign.send_hours_end}:00). Skipping.")
                return
            
            async with SessionLocal() as db:
                one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
                res = await db.execute(select(func.count(EmailLog.id)).where(
                    EmailLog.campaign_id == campaign.id,
                    EmailLog.sent_at >= one_hour_ago
                ))
                emails_sent_last_hour = res.scalar() or 0
            
            if emails_sent_last_hour >= campaign.max_emails_per_hour:
                print(f"🛑 Campaign '{campaign.name}' hit hourly limit ({campaign.max_emails_per_hour}/hr). Skipping.")
                return

            for i, row in enumerate(rows[1:], start=1):
                max_idx = max(name_idx, email_idx, inquiry_idx, phone_idx, status_idx)
                while len(row) <= max_idx:
                    row.append("")
                    
                email = row[email_idx]
                status = row[status_idx]
                
                if not email or "@" not in email:
                    continue
                    
                name = row[name_idx] if name_idx != -1 else ""
                inquiry = row[inquiry_idx] if inquiry_idx != -1 else ""
                
                raw_phone = str(row[phone_idx]) if phone_idx != -1 else ""
                phone = ''.join(filter(str.isdigit, raw_phone))
                
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
                    if getattr(campaign, 'review_mode', False):
                        print(f"⏸️ Campaign '{campaign.name}' in Review Mode. Queuing {email}...")
                        async with SessionLocal() as db:
                            queue_item = EmailQueue(
                                client_id=campaign.client_id,
                                campaign_id=campaign.id,
                                template_id=target_template.id,
                                recipient_email=email,
                                recipient_name=name,
                                status="pending"
                            )
                            db.add(queue_item)
                            await db.commit()
                        
                        # Mark as Queued on the sheet
                        try:
                            await update_sheet_cell(campaign.google_sheet_id, i+1, status_idx + 1, 'Queued')
                        except Exception as e:
                            print(f'❌ Failed to update sheet cell: {e}')
                        continue
                        
                    log_id = str(uuid.uuid4())
                    print(f"📤 Sending '{target_template.project_name}' email to {email}...")
                    success, err = await send_email_via_gmail_api(email, name, target_template, access_token, log_id)
                    
                    whatsapp_success = False
                    whatsapp_err = None
                    
                    use_wa = getattr(campaign, 'use_whatsapp', False)
                    print(f"🧐 WhatsApp Check -> use_whatsapp: {use_wa}, phone: '{phone}'")
                    
                    if use_wa and phone:
                        print(f"💬 Sending WhatsApp message to {phone}...")
                        wa_token = None
                        wa_phone_id = None
                        wa_waba_id = None
                        async with SessionLocal() as wa_db:
                            wa_client = await wa_db.get(Client, campaign.client_id)
                            if wa_client:
                                wa_token = wa_client.whatsapp_access_token
                                wa_phone_id = wa_client.whatsapp_phone_number_id
                                wa_waba_id = wa_client.whatsapp_business_account_id
                                
                        wa_template = getattr(target_template, 'whatsapp_template_name', None) or getattr(campaign, 'default_whatsapp_template_name', None)
                        
                        if wa_token and wa_phone_id and wa_waba_id and wa_template:
                            whatsapp_success, whatsapp_err = await send_whatsapp_message(phone, wa_template, wa_phone_id, wa_waba_id, wa_token, fallback_name=name or "Customer")
                            if whatsapp_success:
                                print(f"✅ WhatsApp sent successfully to {phone}")
                            else:
                                print(f"❌ WhatsApp failed for {phone}: {whatsapp_err}")
                        else:
                            print(f"⚠️ WhatsApp skipped for {phone}: Missing credentials or template name.")
                    
                    if success:
                        print(f"✅ Successfully sent to {email}")
                    else:
                        print(f"❌ Failed to send to {email}: {err}")
                    
                    # Log to DB
                    async with SessionLocal() as db:
                        log = EmailLog(
                                id=log_id,
                            client_id=campaign.client_id,
                            campaign_id=campaign.id,
                            recipient_email=email,
                            recipient_name=name,
                            template_used=target_template.project_name,
                            category_assigned=category,
                            status="sent" if success else "failed",
                            error_message=err,
                            sent_at=datetime.now(timezone.utc) if success else None,
                            is_follow_up=is_follow_up_run,
                            whatsapp_sent=whatsapp_success
                        )
                        db.add(log)
                        if success:
                            db_client = await db.get(Client, campaign.client_id)
                            db_client.emails_sent_today += 1
                        await db.commit()
                        
                    # Queue Sheet Update
                    new_status = "Followed Up" if is_follow_up_run else "Sent"
                    if not success: new_status = "Failed"
                    try:
                        await update_sheet_cell(campaign.google_sheet_id, i+1, status_idx + 1, new_status)
                    except Exception as e:
                        print(f'❌ Failed to update sheet cell: {e}')
                    
                    if success:
                        await asyncio.sleep(1) # Delay between sends
            
            
            async with SessionLocal() as db:
                db_camp = await db.get(Campaign, campaign.id)
                if db_camp:
                    db_camp.last_run_at = datetime.now(timezone.utc)
                await db.commit()
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"💥 Unhandled error in process_single_campaign for campaign {campaign.id}: {e}")

async def run_247_engine():
    """Background loop that polls all campaigns every 60 seconds."""
    print("🚀 24/7 Autonomous Engine Started...")
    
    last_reset_date = datetime.now(timezone.utc).date()
    
    while True:
        try:
            current_date = datetime.now(timezone.utc).date()
            if current_date != last_reset_date:
                print(f"🔄 Midnight reached ({current_date}). Resetting daily email limits for all clients...")
                async with SessionLocal() as db:
                    await db.execute(update(Client).values(emails_sent_today=0))
                    await db.commit()
                last_reset_date = current_date

            async with SessionLocal() as db:
                from backend.models.campaign import Campaign
                campaigns_res = await db.execute(select(Campaign).where(Campaign.is_active == True))
                campaigns = campaigns_res.scalars().all()
                global_settings = await get_global_settings(db)
                
            groq_key = global_settings.get("GROQ_API_KEY", settings.GROQ_API_KEY)
            
            def is_client_allowed(client):
                now = datetime.now(timezone.utc)
                if client.subscription_ends_at and client.subscription_ends_at > now: return True
                if client.trial_ends_at and client.trial_ends_at > now: return True
                return False

            # --- PROCESS APPROVED QUEUED EMAILS ---
            async with SessionLocal() as db:
                queued_res = await db.execute(select(EmailQueue).where(EmailQueue.status == "approved"))
                queued_emails = queued_res.scalars().all()
                for q in queued_emails:
                    db_client = await db.get(Client, q.client_id)
                    if not db_client or db_client.status != "active" or db_client.emails_sent_today >= db_client.daily_email_limit:
                        continue
                        
                    if not is_client_allowed(db_client):
                        print(f"🚫 Skipping queued email for {db_client.company_name}: Trial/Subscription Expired.")
                        continue
                    
                    target_template = await db.get(Template, q.template_id)
                    campaign = await db.get(Campaign, q.campaign_id)
                    if not target_template or not campaign:
                        q.status = "failed"
                        q.error_message = "Missing template or campaign"
                        continue
                        
                    await db.refresh(db_client, ['user'])
                    access_token = await refresh_google_token(db_client.user, db) if db_client.user else None
                    
                    log_id = str(uuid.uuid4())
                    print(f"📤 Sending QUEUED '{target_template.project_name}' email to {q.recipient_email}...")
                    success, err = await send_email_via_gmail_api(q.recipient_email, q.recipient_name or "", target_template, access_token, log_id)
                    
                    # Update Log
                    log = EmailLog(
                                id=log_id,
                        client_id=q.client_id,
                        campaign_id=q.campaign_id,
                        recipient_email=q.recipient_email,
                        recipient_name=q.recipient_name,
                        template_used=target_template.project_name,
                        status="sent" if success else "failed",
                        error_message=err
                    )
                    db.add(log)
                    
                    if success:
                        db_client.emails_sent_today += 1
                        q.status = "sent"
                        # Attempt to update sheet if possible
                        try:
                            # We don't have the row index here, so we could just leave it or search
                            pass
                        except Exception: pass
                    else:
                        q.status = "failed"
                        q.error_message = err

                if queued_emails:
                    await db.commit()
            
            # --- PROCESS CAMPAIGNS ---
            # Enforce limits by grouping campaigns
            client_campaigns = {}
            for c in campaigns:
                if c.client_id not in client_campaigns:
                    client_campaigns[c.client_id] = []
                client_campaigns[c.client_id].append(c)

            allowed_campaigns = []
            async with SessionLocal() as db:
                for cid, camps in client_campaigns.items():
                    db_client = await db.get(Client, cid)
                    if db_client and db_client.status == "active":
                        await db.refresh(db_client, ['plan'])
                        limit = db_client.plan.campaign_limit if db_client.plan else 3
                        camps.sort(key=lambda x: x.created_at)
                        allowed_campaigns.extend(camps[:limit])

            async def run_and_cleanup(camp, g_key):
                try:
                    await process_single_campaign(camp, g_key)
                finally:
                    _running_campaigns.discard(camp.id)

            for camp in allowed_campaigns:
                if camp.id not in _running_campaigns:
                    _running_campaigns.add(camp.id)
                    asyncio.create_task(run_and_cleanup(camp, groq_key))

        except Exception as e:
            print(f"24/7 Engine Iteration Error: {e}")
            


        await asyncio.sleep(60) # Poll every minute
