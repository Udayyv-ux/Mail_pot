"""
Client portal API routes.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional

from backend.database import get_db
from backend.middleware.auth_middleware import require_client, require_active_subscription
from backend.models.client import Client
from backend.models.plan import Plan
from backend.models.template import Template
from backend.models.email_log import EmailLog
from backend.models.email_queue import EmailQueue
from datetime import datetime, timedelta, timezone
from fastapi import UploadFile, File, BackgroundTasks
import os
import uuid
import re
from backend.utils.encryption import encrypt_value
from backend.models.campaign import Campaign
from backend.models.image import UploadedImage
import base64

router = APIRouter(prefix="/api/client", tags=["client"])

async def get_client_profile(user, db: AsyncSession):
    from datetime import datetime, timezone
    result = await db.execute(select(Client).where(Client.user_id == user.id))
    client = result.scalar_one_or_none()
    if not client:
        # If an admin is testing the client portal or a user was manually created, they might not have a client profile yet.
        from backend.models.app_settings import AppSetting
        setting = await db.execute(select(AppSetting).where(AppSetting.key == "trial_days"))
        setting_obj = setting.scalar_one_or_none()
        trial_days = int(setting_obj.value) if setting_obj and setting_obj.value.isdigit() else 5
        
        plan_result = await db.execute(select(Plan).where(Plan.name.ilike('%Ultimat%')))
        ultra_plan = plan_result.scalar_one_or_none()

        client = Client(
            id=str(uuid.uuid4()),
            user_id=user.id,
            company_name=user.name + " Company" if getattr(user, "name", None) else "My Company",
            daily_email_limit=ultra_plan.email_limit_daily if ultra_plan else 1000,
            plan_id=ultra_plan.id if ultra_plan else None,
            trial_ends_at=datetime.now(timezone.utc) + timedelta(days=trial_days)
        )
        db.add(client)
        await db.commit()
        await db.refresh(client)
        
    # Lazy subscription expiration check
    if client.plan_id and client.subscription_ends_at:
        if datetime.now(timezone.utc) > client.subscription_ends_at:
            client.plan_id = None
            client.daily_email_limit = 50  # Default free tier limit
            await db.commit()
            
    return client

@router.get("/dashboard")
async def get_dashboard(db: AsyncSession = Depends(get_db), current_user = Depends(require_client)):
    client = await get_client_profile(current_user, db)
    
    # Count active campaigns — wrapped in try/except to prevent crash if table is missing
    active_campaigns = 0
    total_campaigns = 0
    try:
        result = await db.execute(select(func.count(Campaign.id)).where(Campaign.client_id == client.id, Campaign.is_active == True))
        active_campaigns = result.scalar() or 0
        
        result = await db.execute(select(func.count(Campaign.id)).where(Campaign.client_id == client.id))
        total_campaigns = result.scalar() or 0
    except Exception:
        pass
    
    # Count email logs sent, failed, opened, and recent activity
    try:
        from sqlalchemy import func as sa_func, desc
        log_result = await db.execute(select(func.count(EmailLog.id)).where(
            EmailLog.client_id == client.id, EmailLog.status == "sent"
        ))
        total_emails_sent = log_result.scalar() or 0
        
        failed_result = await db.execute(select(func.count(EmailLog.id)).where(
            EmailLog.client_id == client.id, EmailLog.status == "failed"
        ))
        total_emails_failed = failed_result.scalar() or 0
        
        opened_result = await db.execute(select(func.count(EmailLog.id)).where(
            EmailLog.client_id == client.id, EmailLog.opened == True
        ))
        total_emails_opened = opened_result.scalar() or 0
        
        recent_res = await db.execute(select(EmailLog).where(
            EmailLog.client_id == client.id
        ).order_by(EmailLog.sent_at.desc().nulls_last()).limit(10))
        recent_logs = recent_res.scalars().all()
        recent_activity = [{
            "id": r.id,
            "recipient_email": r.recipient_email,
            "status": r.status,
            "opened": r.opened,
            "sent_at": r.sent_at.isoformat() if r.sent_at else None,
            "error_message": r.error_message
        } for r in recent_logs]
    except Exception as e:
        total_emails_sent = client.emails_sent_today
        total_emails_failed = 0
        total_emails_opened = 0
        recent_activity = []
    
    return {
        "emails_sent_today": client.emails_sent_today,
        "daily_limit": client.daily_email_limit,
        "active_campaigns": active_campaigns,
        "total_campaigns": total_campaigns,
        "total_emails_sent": total_emails_sent,
        "total_emails_failed": total_emails_failed,
        "total_emails_opened": total_emails_opened,
        "recent_activity": recent_activity,
        "company_name": client.company_name
    }

@router.get("/profile")
async def get_profile(db: AsyncSession = Depends(get_db), current_user = Depends(require_client)):
    from backend.config import settings
    import json
    
    client = await get_client_profile(current_user, db)
    
    service_email = "Admin has not configured the Service Account yet"
    if settings.GOOGLE_SERVICE_ACCOUNT_JSON:
        try:
            creds = json.loads(settings.GOOGLE_SERVICE_ACCOUNT_JSON)
            service_email = creds.get("client_email", service_email)
        except:
            pass
    
    plan_name = "Free"
    daily_limit = client.daily_email_limit
    has_ai = False
    if client.plan:
        plan_name = client.plan.name
        daily_limit = client.plan.email_limit_daily
        has_ai = getattr(client.plan, 'has_ai_templates', False)
        
    # Check expiration
    now = datetime.now(timezone.utc)
    is_expired = True
    if client.subscription_ends_at and client.subscription_ends_at > now: is_expired = False
    elif client.trial_ends_at and client.trial_ends_at > now: is_expired = False
    
    if is_expired:
        plan_name = "Trial Expired"
            
    from backend.models.user import UserRole
    if current_user.role == UserRole.ADMIN:
        plan_name = "Super Admin (Unlimited)"
        daily_limit = 99999999
        has_ai = True
        if client.trial_ends_at is not None or client.daily_email_limit != 99999999:
            client.trial_ends_at = None
            client.daily_email_limit = 99999999
            await db.commit()

    def format_dt(dt):
        if not dt: return None
        s = dt.isoformat()
        if not s.endswith('Z') and '+' not in s and '-' not in s[11:]:
            return s + 'Z'
        return s

    return {
        "company_name": client.company_name,
        "service_account_email": service_email,
        "plan_name": plan_name,
        "daily_limit": daily_limit,
        "has_ai_templates": has_ai,
        "whatsapp_access_token": client.whatsapp_access_token,
        "whatsapp_phone_number_id": client.whatsapp_phone_number_id,
        "whatsapp_business_account_id": client.whatsapp_business_account_id,
        "trial_ends_at": format_dt(client.trial_ends_at),
        "subscription_ends_at": format_dt(client.subscription_ends_at)
    }

class ProfileUpdate(BaseModel):
    company_name: Optional[str] = None
    whatsapp_access_token: Optional[str] = None
    whatsapp_phone_number_id: Optional[str] = None
    whatsapp_business_account_id: Optional[str] = None

@router.put("/profile")
async def update_profile(profile: ProfileUpdate, db: AsyncSession = Depends(get_db), current_user = Depends(require_active_subscription)):
    client = await get_client_profile(current_user, db)
    if profile.company_name is not None:
        client.company_name = profile.company_name
    if profile.whatsapp_access_token is not None:
        client.whatsapp_access_token = profile.whatsapp_access_token
    if profile.whatsapp_phone_number_id is not None:
        client.whatsapp_phone_number_id = profile.whatsapp_phone_number_id
    if profile.whatsapp_business_account_id is not None:
        client.whatsapp_business_account_id = profile.whatsapp_business_account_id
    await db.commit()
    return {"status": "success"}

@router.get("/whatsapp/templates")
async def get_whatsapp_templates(db: AsyncSession = Depends(get_db), current_user = Depends(require_client)):
    import httpx
    client = await get_client_profile(current_user, db)
    if not client.whatsapp_business_account_id or not client.whatsapp_access_token:
        raise HTTPException(status_code=400, detail="WhatsApp Business Account ID and Access Token are required to fetch templates")
    
    url = f"https://graph.facebook.com/v25.0/{client.whatsapp_business_account_id}/message_templates?limit=100"
    headers = {"Authorization": f"Bearer {client.whatsapp_access_token}"}
    
    async with httpx.AsyncClient() as http_client:
        response = await http_client.get(url, headers=headers)
        if response.status_code != 200:
            raise HTTPException(status_code=400, detail=response.json().get("error", {}).get("message", "Failed to fetch templates"))
        
        return response.json()

# --- CAMPAIGNS ---

class CampaignCreate(BaseModel):
    name: str
    sheet_url_or_id: str
    target_columns: str = "Name, Email, Inquiry"
    status_column: str = "Status"
    inquiry_column: str = "Inquiry"
    default_template_id: Optional[str] = None
    use_whatsapp: bool = False
    default_whatsapp_template_name: Optional[str] = None
    follow_up_days: int = 0
    follow_up_template_id: Optional[str] = None
    follow_up_whatsapp_template_name: Optional[str] = None
    follow_up_condition: str = "always"
    max_emails_per_hour: int = 50
    send_hours_start: int = 9
    send_hours_end: int = 17
    review_mode: bool = False

class CampaignUpdate(BaseModel):
    name: Optional[str] = None
    sheet_url_or_id: Optional[str] = None
    target_columns: Optional[str] = None
    status_column: Optional[str] = None
    inquiry_column: Optional[str] = None
    default_template_id: Optional[str] = None
    use_whatsapp: Optional[bool] = None
    default_whatsapp_template_name: Optional[str] = None
    follow_up_days: Optional[int] = None
    follow_up_template_id: Optional[str] = None
    follow_up_whatsapp_template_name: Optional[str] = None
    follow_up_condition: Optional[str] = None
    max_emails_per_hour: Optional[int] = None
    send_hours_start: Optional[int] = None
    send_hours_end: Optional[int] = None
    review_mode: Optional[bool] = None

@router.get("/campaigns")
async def list_campaigns(db: AsyncSession = Depends(get_db), current_user = Depends(require_client)):
    client = await get_client_profile(current_user, db)
    result = await db.execute(select(Campaign).where(Campaign.client_id == client.id).order_by(Campaign.created_at.desc()))
    campaigns = result.scalars().all()
    return [{
        "id": c.id,
        "name": c.name,
        "google_sheet_id": c.google_sheet_id,
        "target_columns": c.target_columns,
        "status_column": c.status_column,
        "inquiry_column": getattr(c, 'inquiry_column', 'Inquiry'),
        "default_template_id": c.default_template_id,
        "use_whatsapp": getattr(c, 'use_whatsapp', False),
        "default_whatsapp_template_name": getattr(c, 'default_whatsapp_template_name', None),
        "follow_up_days": c.follow_up_days,
        "follow_up_template_id": c.follow_up_template_id,
        "follow_up_whatsapp_template_name": c.follow_up_whatsapp_template_name,
        "follow_up_condition": getattr(c, 'follow_up_condition', 'always'),
        "max_emails_per_hour": c.max_emails_per_hour,
        "send_hours_start": c.send_hours_start,
        "send_hours_end": c.send_hours_end,
        "review_mode": getattr(c, 'review_mode', False),
        "is_active": c.is_active,
        "created_at": c.created_at,
        "last_error": c.last_error,
        "last_run_at": c.last_run_at.isoformat() if getattr(c, 'last_run_at', None) else None
    } for c in campaigns]

@router.post("/campaigns")
async def create_campaign(data: CampaignCreate, db: AsyncSession = Depends(get_db), current_user = Depends(require_active_subscription)):
    client = await get_client_profile(current_user, db)
    await db.refresh(client, ['plan'])
    
    # Enforce limits
    campaign_limit = client.plan.campaign_limit if client.plan else 3
    result = await db.execute(select(func.count(Campaign.id)).where(Campaign.client_id == client.id))
    current_count = result.scalar() or 0
    if current_count >= campaign_limit:
        raise HTTPException(status_code=403, detail=f"Your plan is limited to {campaign_limit} campaigns. Please upgrade.")
        
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', data.sheet_url_or_id)
    sheet_id = match.group(1) if match else data.sheet_url_or_id.strip()
    
    new_campaign = Campaign(
        client_id=client.id,
        name=data.name,
        google_sheet_id=sheet_id,
        target_columns=data.target_columns,
        status_column=data.status_column,
        inquiry_column=data.inquiry_column,
        default_template_id=data.default_template_id,
        use_whatsapp=data.use_whatsapp,
        default_whatsapp_template_name=data.default_whatsapp_template_name,
        follow_up_days=data.follow_up_days,
        follow_up_template_id=data.follow_up_template_id,
        follow_up_whatsapp_template_name=data.follow_up_whatsapp_template_name,
        follow_up_condition=data.follow_up_condition,
        max_emails_per_hour=data.max_emails_per_hour,
        send_hours_start=data.send_hours_start,
        send_hours_end=data.send_hours_end,
        review_mode=data.review_mode
    )
    db.add(new_campaign)
    await db.commit()
    await db.refresh(new_campaign)
    return {"status": "success", "campaign_id": new_campaign.id}

@router.put("/campaigns/{campaign_id}")
async def update_campaign(campaign_id: str, data: CampaignUpdate, db: AsyncSession = Depends(get_db), current_user = Depends(require_active_subscription)):
    client = await get_client_profile(current_user, db)
    
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id, Campaign.client_id == client.id))
    campaign = result.scalar_one_or_none()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    update_data = data.model_dump(exclude_unset=True)
    
    if 'sheet_url_or_id' in update_data:
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', update_data['sheet_url_or_id'])
        sheet_id = match.group(1) if match else update_data['sheet_url_or_id'].strip()
        campaign.google_sheet_id = sheet_id
        del update_data['sheet_url_or_id']
        
    for key, value in update_data.items():
        setattr(campaign, key, value)
        
    await db.commit()
    await db.refresh(campaign)
    return {"status": "success", "campaign_id": campaign.id}

@router.delete("/campaigns/{campaign_id}")
async def delete_campaign(campaign_id: str, db: AsyncSession = Depends(get_db), current_user = Depends(require_active_subscription)):
    client = await get_client_profile(current_user, db)
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id, Campaign.client_id == client.id))
    campaign = result.scalar_one_or_none()
    if campaign:
        await db.delete(campaign)
        await db.commit()
    return {"status": "success"}

@router.get("/notifications")
async def get_client_notifications(db: AsyncSession = Depends(get_db), current_user = Depends(require_client)):
    from backend.models.app_settings import Notification
    # Fetch active notifications
    result = await db.execute(select(Notification).where(Notification.is_active == True).order_by(Notification.created_at.desc()))
    return result.scalars().all()

@router.get("/analytics/chart")
async def get_client_chart(db: AsyncSession = Depends(get_db), current_user = Depends(require_client)):
    client = await get_client_profile(current_user, db)
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    result = await db.execute(select(EmailLog.sent_at, EmailLog.whatsapp_sent).where(
        EmailLog.client_id == client.id, 
        EmailLog.sent_at >= seven_days_ago
    ))
    logs = result.all()
    labels = []
    email_data = []
    whatsapp_data = []
    for i in range(6, -1, -1):
        d = datetime.now(timezone.utc) - timedelta(days=i)
        labels.append(d.strftime("%Y-%m-%d"))
        email_data.append(0)
        whatsapp_data.append(0)
    
    for row in logs:
        sent_at = row.sent_at
        wa_sent = getattr(row, 'whatsapp_sent', False)
        if not sent_at: continue
        date_str = sent_at.strftime("%Y-%m-%d")
        if date_str in labels:
            idx = labels.index(date_str)
            if wa_sent:
                whatsapp_data[idx] += 1
            
            email_was_sent = bool(getattr(row, 'thread_id', None)) or not wa_sent
            if email_was_sent:
                email_data[idx] += 1
            
    return {"labels": labels, "email_data": email_data, "whatsapp_data": whatsapp_data}

@router.post("/upload")
async def upload_image(file: UploadFile = File(...), db: AsyncSession = Depends(get_db), current_user = Depends(require_active_subscription)):
    client = await get_client_profile(current_user, db)
    
    contents = await file.read()
    b64 = base64.b64encode(contents).decode("utf-8")
    mime = file.content_type or "image/png"
    data_uri = f"data:{mime};base64,{b64}"
    
    img = UploadedImage(client_id=client.id, data_uri=data_uri)
    db.add(img)
    await db.commit()
    
    return {"url": f"/api/images/{img.id}"}
@router.get("/queue")
async def list_email_queue(db: AsyncSession = Depends(get_db), current_user = Depends(require_client)):
    client = await get_client_profile(current_user, db)
    from sqlalchemy.orm import selectinload
    res = await db.execute(select(EmailQueue).options(selectinload(EmailQueue.campaign), selectinload(EmailQueue.template)).where(EmailQueue.client_id == client.id, EmailQueue.status == "pending").order_by(EmailQueue.created_at.desc()))
    queue = res.scalars().all()
    return [{
        "id": q.id,
        "campaign_name": q.campaign.name if q.campaign else "Unknown",
        "template_name": q.template.project_name if q.template else "Unknown",
        "recipient_email": q.recipient_email,
        "recipient_name": q.recipient_name,
        "status": q.status,
        "created_at": q.created_at
    } for q in queue]

@router.post("/queue/{id}/approve")
async def approve_queue_item(id: str, db: AsyncSession = Depends(get_db), current_user = Depends(require_active_subscription)):
    client = await get_client_profile(current_user, db)
    item = await db.get(EmailQueue, id)
    if not item or item.client_id != client.id: raise HTTPException(404, "Item not found")
    item.status = "approved"
    await db.commit()
    return {"status": "success"}

@router.post("/queue/{id}/reject")
async def reject_queue_item(id: str, db: AsyncSession = Depends(get_db), current_user = Depends(require_active_subscription)):
    client = await get_client_profile(current_user, db)
    item = await db.get(EmailQueue, id)
    if not item or item.client_id != client.id: raise HTTPException(404, "Item not found")
    item.status = "rejected"
    await db.commit()
    return {"status": "success"}

@router.get("/inbox")
async def get_inbox(db: AsyncSession = Depends(get_db), current_user = Depends(require_client)):
    client = await get_client_profile(current_user, db)
    await db.refresh(client, ['user'])
    from backend.services.email_engine import refresh_google_token
    import httpx
    
    access_token = await refresh_google_token(client.user, db)
    if not access_token:
        raise HTTPException(400, "No Google connection")
        
    async with httpx.AsyncClient() as http_client:
        # Fetch latest messages from INBOX
        resp = await http_client.get(
            "https://gmail.googleapis.com/gmail/v1/users/me/messages?labelIds=INBOX&maxResults=20",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if resp.status_code != 200:
            raise HTTPException(400, "Failed to fetch inbox")
            
        data = resp.json()
        messages = data.get("messages", [])
        
        inbox_items = []
        for m in messages:
            msg_resp = await http_client.get(
                f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{m['id']}?format=metadata&metadataHeaders=From&metadataHeaders=Subject&metadataHeaders=Date",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            if msg_resp.status_code == 200:
                msg_data = msg_resp.json()
                headers = {h['name']: h['value'] for h in msg_data.get('payload', {}).get('headers', [])}
                inbox_items.append({
                    "id": m['id'],
                    "threadId": m['threadId'],
                    "snippet": msg_data.get('snippet', ''),
                    "from": headers.get('From', ''),
                    "subject": headers.get('Subject', ''),
                    "date": headers.get('Date', '')
                })
                
    return inbox_items




# --- WHATSAPP WEBHOOK ---
@router.get("/whatsapp/webhook")
async def verify_whatsapp_webhook(request: Request):
    hub_mode = request.query_params.get("hub.mode")
    hub_challenge = request.query_params.get("hub.challenge")
    hub_verify_token = request.query_params.get("hub.verify_token")
    if hub_verify_token == "sheetx_whatsapp":
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse(hub_challenge)
    return {"error": "Invalid token"}

@router.post("/whatsapp/webhook")
async def receive_whatsapp_webhook(payload: dict):
    import json
    print("\n================ WA WEBHOOK ================")
    print(json.dumps(payload, indent=2))
    print("============================================\n")
    return {"status": "ok"}
