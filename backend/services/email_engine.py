"""
Autonomous 24/7 Engine — Handles Google Sheets polling, AI categorization, and HTTP Email Blasting.
"""
import asyncio
import random
from datetime import datetime, timezone
import httpx
from groq import Groq, AsyncGroq
from sqlalchemy import select, func

from backend.config import settings
from backend.database import SessionLocal
from backend.models.client import Client
from backend.models.campaign import Campaign
from backend.models.template import Template
from backend.models.email_log import EmailLog
from backend.models.email_queue import EmailQueue
from backend.models.app_settings import AppSetting
from backend.services.sheets_service import get_sheet_data, update_sheet_cell, update_sheet_cells_batch
from backend.services.whatsapp_service import send_whatsapp_message
import base64
from email.message import EmailMessage


def get_col_index(headers: list, target_name: str) -> int:
    for i, h in enumerate(headers):
        if h.strip().lower() == target_name.strip().lower():
            return i
    return -1

async def get_global_settings(db) -> dict:
    res = await db.execute(select(AppSetting))
    settings_db = res.scalars().all()
    return {s.key: s.value for s in settings_db}

async def categorize_with_ai(lead_info: str, templates: list, groq_key: str) -> str:
    """Use Groq AI to categorize a lead into one of the available templates."""
    if not lead_info or not templates:
        return "General"
    categories = [t.project_name for t in templates if t.is_active]
    
    if len(categories) == 1:
        return categories[0]
        
    categories_context = "\n".join([f"- '{t.project_name}': This template is an email with subject '{t.subject}'" for t in templates if t.is_active])
    
    system_prompt = (
        "You are an expert email categorization AI. Your job is to read a customer inquiry or notes, "
        "and select the MOST APPROPRIATE email template category to send them.\n\n"
        "Here are the available categories:\n"
        f"{categories_context}\n\n"
        "You must choose EXACTLY ONE category name from the list above. "
        "If the inquiry does not clearly match any of the categories, output EXACTLY the word 'General'. "
        "Output ONLY the exact category name. Do not wrap it in quotes. Do not add any explanation."
    )
    prompt = f"Customer Inquiry / Lead Notes: '{lead_info}'\n\nWhich category does this fit best?"
    
    try:
        api_key = groq_key if groq_key else settings.GROQ_API_KEY
        client = AsyncGroq(api_key=api_key)
        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.0
        )
        decision = response.choices[0].message.content.strip()
        decision = decision.strip("'").strip('"')
        
        print(f"AI Categorized '{lead_info}' -> '{decision}'")
        
        if decision in categories:
            return decision
            
        decision_lower = decision.lower()
        
        for c in categories:
            if c.lower() in decision_lower:
                return c
                
        if len(decision_lower) > 3:
            for c in categories:
                if decision_lower in c.lower():
                    return c
                    
        return "General"
    except Exception as e:
        print(f"AI Categorization error: {e}")
        return "General"

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

async def send_email_via_gmail_api(to_email: str, first_name: str, template, access_token: str) -> tuple[bool, str]:
    if not access_token:
        return False, "Client user has not authenticated with Google or access token is missing."
    
    subject = template.subject
    greeting_name = first_name.strip() if first_name and str(first_name).strip() else "Customer"
    html_body = f"<p>Dear {greeting_name},</p><br>" + template.body_html.replace("{first_name}", first_name or "There")
    
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
                data = resp.json()
                return True, data.get("threadId", "")
            elif resp.status_code == 401:
                return False, f"Gmail API 401 Unauthorized. Exact response: {resp.text}"
            return False, f"Gmail API Error: {resp.text}"
    except Exception as e:
        return False, f"HTTP Error: {str(e)}"

async def process_single_client(client_id: int, queued_email_ids: list[int], campaign_ids: list[int], groq_key: str):
    """Processes all queued emails and campaigns for ONE specific client sequentially to prevent spam penalties."""
    
    # --- 1. PROCESS QUEUED EMAILS FOR THIS CLIENT ---
    for q_id in queued_email_ids:
        async with SessionLocal() as db:
            q = await db.get(EmailQueue, q_id)
            if not q or q.status != "approved":
                continue
                
            db_client = await db.get(Client, client_id)
            if not db_client or db_client.status != "active" or db_client.emails_sent_today >= db_client.daily_email_limit:
                continue
            
            target_template = await db.get(Template, q.template_id)
            campaign = await db.get(Campaign, q.campaign_id)
            if not target_template or not campaign:
                q.status = "failed"
                q.error_message = "Missing template or campaign"
                await db.commit()
                continue
                
            await db.refresh(db_client, ['user'])
            access_token = await refresh_google_token(db_client.user, db) if db_client.user else None
            
            print(f"📤 Sending QUEUED '{target_template.project_name}' email to {q.recipient_email}...")
            success, thread_id_or_err = await send_email_via_gmail_api(q.recipient_email, q.recipient_name or "", target_template, access_token)
            
            log = EmailLog(
                client_id=client_id,
                campaign_id=q.campaign_id,
                recipient_email=q.recipient_email,
                recipient_name=q.recipient_name,
                template_used=target_template.project_name,
                status="sent" if success else "failed",
                error_message="" if success else thread_id_or_err,
                thread_id=thread_id_or_err if success else None
            )
            db.add(log)
            
            if success:
                db_client.emails_sent_today += 1
                q.status = "sent"
            else:
                q.status = "failed"
                q.error_message = thread_id_or_err
                
            await db.commit()
            
            if success:
                # Human Simulation: Randomized Delay
                await asyncio.sleep(random.uniform(2.5, 6.0))

    # --- 2. PROCESS CAMPAIGNS FOR THIS CLIENT ---
    for camp_id in campaign_ids:
        async with SessionLocal() as db:
            campaign = await db.get(Campaign, camp_id)
            if not campaign or not campaign.is_active:
                continue
                
            db_client = await db.get(Client, client_id)
            if not db_client or db_client.status != "active":
                continue
                
            if db_client.emails_sent_today >= db_client.daily_email_limit:
                print(f"⚠️ Skipping campaign {campaign.id} - Client daily limit reached ({db_client.emails_sent_today}/{db_client.daily_email_limit})")
                continue
                
            templates_res = await db.execute(select(Template).where(Template.client_id == client_id, Template.is_active == True))
            templates = templates_res.scalars().all()
            
            await db.refresh(db_client, ['user'])
            client_user = db_client.user
            
            access_token = None
            if client_user:
                access_token = await refresh_google_token(client_user, db)
                
            if not templates: continue
            
            # Re-read campaign inside try block to ensure fresh data
            camp_name = campaign.name
            camp_google_sheet_id = campaign.google_sheet_id
            camp_target_columns = campaign.target_columns
            camp_status_column = campaign.status_column
            camp_inquiry_column = getattr(campaign, 'inquiry_column', 'Inquiry')
            camp_follow_up_days = campaign.follow_up_days
            camp_follow_up_template_id = campaign.follow_up_template_id
            camp_default_template_id = getattr(campaign, 'default_template_id', None)
            camp_review_mode = getattr(campaign, 'review_mode', False)
            camp_use_whatsapp = getattr(campaign, 'use_whatsapp', False)
            camp_max_emails_per_hour = campaign.max_emails_per_hour
            
            # Check hourly limits
            one_hour_ago = datetime.now(timezone.utc) - __import__('datetime').timedelta(hours=1)
            res = await db.execute(select(func.count(EmailLog.id)).where(
                EmailLog.campaign_id == campaign.id,
                EmailLog.sent_at >= one_hour_ago
            ))
            emails_sent_last_hour = res.scalar() or 0
            
            if emails_sent_last_hour >= camp_max_emails_per_hour:
                print(f"🛑 Campaign '{camp_name}' hit hourly limit ({camp_max_emails_per_hour}/hr). Skipping.")
                continue

        try:
            _, rows = await get_sheet_data(camp_google_sheet_id)
            async with SessionLocal() as db:
                db_camp = await db.get(Campaign, camp_id)
                if db_camp: db_camp.last_error = None
                await db.commit()
        except Exception as e:
            print(f"❌ Failed to read sheet for Campaign {camp_id}: {e}")
            async with SessionLocal() as db:
                db_camp = await db.get(Campaign, camp_id)
                if db_camp: db_camp.last_error = f"Failed to read sheet: {str(e)}"
                await db.commit()
            continue
            
        if not rows or len(rows) < 2: 
            async with SessionLocal() as db:
                db_camp = await db.get(Campaign, camp_id)
                if db_camp: db_camp.last_error = "Sheet is empty or missing headers."
                await db.commit()
            continue
            
        headers = rows[0]
        target_cols = [c.strip() for c in (camp_target_columns or "Name, Email, Inquiry").split(',')]
        status_col_name = camp_status_column or "Status"
        
        name_col = target_cols[0] if len(target_cols) > 0 else "Name"
        email_col = target_cols[1] if len(target_cols) > 1 else "Email"
        phone_col = target_cols[2] if len(target_cols) > 2 else "Phone"
        
        name_idx = get_col_index(headers, name_col)
        email_idx = get_col_index(headers, email_col)
        phone_idx = get_col_index(headers, phone_col)
        inquiry_idx = get_col_index(headers, camp_inquiry_column)
        status_idx = get_col_index(headers, status_col_name)
        location_idx = get_col_index(headers, "Location")
        
        if (email_idx == -1 and phone_idx == -1) or status_idx == -1:
            async with SessionLocal() as db:
                db_camp = await db.get(Campaign, camp_id)
                if db_camp: db_camp.last_error = f"Missing Email/Phone or {status_col_name} column."
                await db.commit()
            continue

        batch_updates = []
        for i, row in enumerate(rows[1:], start=1):
            while len(row) <= max(name_idx, email_idx, phone_idx, inquiry_idx, status_idx):
                row.append("")
                
            email = row[email_idx] if email_idx != -1 else ""
            phone = row[phone_idx] if phone_idx != -1 else ""
            status = row[status_idx]
            
            has_valid_email = bool(email and "@" in email)
            has_valid_phone = bool(phone and any(c.isdigit() for c in str(phone)))
            
            if not has_valid_email and not has_valid_phone:
                continue
                
            name = row[name_idx] if name_idx != -1 else ""
            
            ai_context_parts = []
            inquiry = row[inquiry_idx] if inquiry_idx != -1 and inquiry_idx < len(row) else ""
            if inquiry.strip():
                ai_context_parts.append(f"{camp_inquiry_column}: {inquiry.strip()}")
                
            for tc in target_cols:
                if tc.lower() in [camp_inquiry_column.lower(), email_col.lower(), phone_col.lower(), name_col.lower()]:
                    continue
                idx = get_col_index(headers, tc)
                if idx != -1 and idx < len(row) and row[idx].strip():
                    ai_context_parts.append(f"{tc}: {row[idx].strip()}")
                    
            if not ai_context_parts:
                for idx, header in enumerate(headers):
                    if idx < len(row) and row[idx].strip() and idx not in (email_idx, phone_idx, status_idx, name_idx):
                        ai_context_parts.append(f"{header.strip()}: {row[idx].strip()}")
                        
            lead_info = " | ".join(ai_context_parts)
            
            target_template = None
            category = "General"
            is_follow_up_run = False
            
            if status.strip().lower() == "sent" and camp_follow_up_days > 0 and camp_follow_up_template_id:
                async with SessionLocal() as db:
                    res = await db.execute(select(EmailLog).where(
                        EmailLog.campaign_id == camp_id,
                        EmailLog.recipient_email == email,
                        EmailLog.is_follow_up == False,
                        EmailLog.status == "sent"
                    ).order_by(EmailLog.sent_at.desc()))
                    last_log = res.scalars().first()
                    
                    if last_log and last_log.sent_at:
                        days_since = (datetime.now(timezone.utc) - last_log.sent_at).days
                        if days_since >= camp_follow_up_days:
                            target_template = await db.get(Template, camp_follow_up_template_id)
                            is_follow_up_run = True
                            category = "FollowUp"

            elif status.strip() == "":
                print(f"📩 Found new lead: {email or phone}")
                category = await categorize_with_ai(lead_info, templates, groq_key)
                target_template = next((t for t in templates if t.project_name == category), None)
                
                if not target_template:
                    if camp_default_template_id:
                        target_template = next((t for t in templates if t.id == camp_default_template_id), None)
                        if target_template:
                            category = "DefaultFallback"
                    else:
                        print(f"⚠️ AI returned '{category}' which has no exact match and no default template is set. Skipping.")
                        target_template = None
                        
                if not target_template:
                    if status_idx >= 0:
                        batch_updates.append({'row': i+1, 'col': status_idx + 1, 'value': 'Unmatched'})
                    continue

            if target_template:
                if camp_review_mode:
                    print(f"⏸️ Campaign '{camp_name}' in Review Mode. Queuing {email or phone}...")
                    async with SessionLocal() as db:
                        queue_item = EmailQueue(
                            client_id=client_id,
                            campaign_id=camp_id,
                            template_id=target_template.id,
                            recipient_email=email,
                            recipient_name=name,
                            status="pending"
                        )
                        db.add(queue_item)
                        await db.commit()
                    
                    if status_idx >= 0:
                        batch_updates.append({'row': i+1, 'col': status_idx + 1, 'value': 'Queued'})
                    continue
                    
                email_success, wa_success = False, False
                email_err, wa_err = "", ""
                
                async with SessionLocal() as db:
                    db_client_inner = await db.get(Client, client_id)
                    wa_token = getattr(db_client_inner, 'whatsapp_access_token', None)
                    wa_phone_id = getattr(db_client_inner, 'whatsapp_phone_number_id', None)
                
                if camp_use_whatsapp and has_valid_phone and getattr(target_template, 'whatsapp_template_name', None) and wa_token:
                    print(f"📱 Sending WhatsApp '{target_template.whatsapp_template_name}' to {phone}...")
                    location = row[location_idx] if location_idx != -1 and len(row) > location_idx else ""
                    wa_success, wa_err = await send_whatsapp_message(
                        phone=phone,
                        template_name=target_template.whatsapp_template_name,
                        access_token=wa_token,
                        phone_number_id=wa_phone_id,
                        variables=[name, getattr(target_template, 'project_name', ''), location]
                    )
                    if wa_success:
                        print(f"✅ WhatsApp sent to {phone}")
                    else:
                        print(f"❌ WhatsApp failed for {phone}: {wa_err}")
                
                if has_valid_email:
                    print(f"📤 Sending '{target_template.project_name}' email to {email}...")
                    email_success, thread_id_or_err = await send_email_via_gmail_api(email, name, target_template, access_token)
                    if email_success:
                        email_err = ""
                        print(f"✅ Email sent to {email}")
                    else:
                        email_err = thread_id_or_err
                        print(f"❌ Email failed for {email}: {email_err}")
                        
                success = email_success or wa_success
                err_msgs = []
                if email_err: err_msgs.append(f"Email: {email_err}")
                if wa_err: err_msgs.append(f"WA: {wa_err}")
                err = " | ".join(err_msgs)
                
                async with SessionLocal() as db:
                    log = EmailLog(
                        client_id=client_id,
                        campaign_id=camp_id,
                        recipient_email=email or phone,
                        recipient_name=name,
                        template_used=target_template.project_name,
                        category_assigned=category,
                        status="sent" if success else "failed",
                        error_message=err,
                        sent_at=datetime.now(timezone.utc) if success else None,
                        is_follow_up=is_follow_up_run,
                        whatsapp_sent=wa_success,
                        thread_id=thread_id_or_err if email_success else None
                    )
                    db.add(log)
                    if email_success:
                        db_client_inner = await db.get(Client, client_id)
                        db_client_inner.emails_sent_today += 1
                    await db.commit()
                    
                if not success:
                    new_status = "Failed"
                elif email_success and wa_success:
                    new_status = "Followed Up (Email & WA)" if is_follow_up_run else "Sent (Email & WA)"
                elif wa_success:
                    new_status = "Followed Up (WA)" if is_follow_up_run else "Sent (WA)"
                else:
                    new_status = "Followed Up" if is_follow_up_run else "Sent"
                    
                if status_idx >= 0:
                    batch_updates.append({'row': i+1, 'col': status_idx + 1, 'value': new_status})
                
                if success:
                    # Human simulation anti-spam delay
                    await asyncio.sleep(random.uniform(2.5, 6.0))
        
        if batch_updates:
            try:
                print(f"📝 Batch updating {len(batch_updates)} sheet cells for '{camp_name}'...")
                await update_sheet_cells_batch(camp_google_sheet_id, batch_updates)
            except Exception as e:
                print(f"❌ Failed to batch update sheet: {e}")
        
        async with SessionLocal() as db:
            db_camp = await db.get(Campaign, camp_id)
            if db_camp:
                db_camp.last_run_at = datetime.now(timezone.utc)
            await db.commit()

async def run_247_engine():
    """Background loop that polls all campaigns every 60 seconds using multi-threading."""
    print("🚀 24/7 Autonomous Engine Started (Multi-Threaded)...")
    semaphore = asyncio.Semaphore(100) # Process up to 100 clients simultaneously
    
    while True:
        try:
            async with SessionLocal() as db:
                from backend.models.campaign import Campaign
                campaigns_res = await db.execute(select(Campaign).where(Campaign.is_active == True))
                campaigns = campaigns_res.scalars().all()
                global_settings = await get_global_settings(db)
                
                queued_res = await db.execute(select(EmailQueue).where(EmailQueue.status == "approved"))
                all_queued_emails = queued_res.scalars().all()
                
            groq_key = global_settings.get("GROQ_API_KEY", settings.GROQ_API_KEY)
            
            # Group data by client to enforce per-client sequential boundaries
            client_data = {}
            for q in all_queued_emails:
                if q.client_id not in client_data:
                    client_data[q.client_id] = {"queued_ids": [], "campaign_ids": []}
                client_data[q.client_id]["queued_ids"].append(q.id)
                
            for c in campaigns:
                if c.client_id not in client_data:
                    client_data[c.client_id] = {"queued_ids": [], "campaign_ids": []}
                client_data[c.client_id]["campaign_ids"].append(c.id)

            # Enforce campaign limits per client
            async with SessionLocal() as db:
                for cid, data in list(client_data.items()):
                    db_client = await db.get(Client, cid)
                    if db_client and db_client.status == "active":
                        await db.refresh(db_client, ['plan'])
                        limit = db_client.plan.campaign_limit if db_client.plan else 3
                        # We don't have created_at mapped on IDs easily without query, 
                        # but since they are already roughly ordered by DB fetch, we just truncate
                        data["campaign_ids"] = data["campaign_ids"][:limit]
                    else:
                        del client_data[cid]

            async def sem_process_client(cid, data):
                async with semaphore:
                    try:
                        await process_single_client(cid, data["queued_ids"], data["campaign_ids"], groq_key)
                    except Exception as e:
                        print(f"❌ Error processing client {cid}: {e}")

            # Execute all active clients simultaneously
            tasks = [sem_process_client(cid, data) for cid, data in client_data.items()]
            if tasks:
                await asyncio.gather(*tasks)
                
        except Exception as e:
            print(f"24/7 Engine Iteration Error: {e}")

        await asyncio.sleep(15) # Poll every 15 seconds
