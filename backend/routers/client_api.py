"""
Client portal API routes.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional

from backend.database import get_db
from backend.middleware.auth_middleware import require_client
from backend.models.client import Client
from backend.models.email_log import EmailLog
from datetime import datetime, timedelta, timezone
from fastapi import UploadFile, File, BackgroundTasks
import os
import uuid
import re
from backend.utils.encryption import encrypt_value
from backend.models.campaign import Campaign

router = APIRouter(prefix="/api/client", tags=["client"])

async def get_client_profile(user, db: AsyncSession):
    result = await db.execute(select(Client).where(Client.user_id == user.id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=404, detail="Client profile not found")
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
    
    # Count email logs sent
    try:
        from sqlalchemy import func as sa_func
        log_result = await db.execute(select(func.count(EmailLog.id)).where(
            EmailLog.client_id == client.id, EmailLog.status == "sent"
        ))
        total_emails_sent = log_result.scalar() or 0
    except Exception:
        total_emails_sent = client.emails_sent_today
    
    return {
        "emails_sent_today": client.emails_sent_today,
        "daily_limit": client.daily_email_limit,
        "active_campaigns": active_campaigns,
        "total_campaigns": total_campaigns,
        "total_emails_sent": total_emails_sent,
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
    if client.plan:
        plan_name = client.plan.name
        daily_limit = client.plan.email_limit_daily
            
    return {
        "company_name": client.company_name,
        "service_account_email": service_email,
        "plan_name": plan_name,
        "daily_limit": daily_limit,
    }

class ProfileUpdate(BaseModel):
    company_name: Optional[str] = None

@router.put("/profile")
async def update_profile(profile: ProfileUpdate, db: AsyncSession = Depends(get_db), current_user = Depends(require_client)):
    client = await get_client_profile(current_user, db)
    if profile.company_name is not None:
        client.company_name = profile.company_name
    await db.commit()
    return {"status": "success"}

# --- CAMPAIGNS ---

class CampaignCreate(BaseModel):
    name: str
    sheet_url_or_id: str
    target_columns: str = "Name, Email, Inquiry"
    status_column: str = "Status"
    follow_up_days: int = 0
    follow_up_template_id: Optional[str] = None

@router.get("/campaigns")
async def list_campaigns(db: AsyncSession = Depends(get_db), current_user = Depends(require_client)):
    client = await get_client_profile(current_user, db)
    result = await db.execute(select(Campaign).where(Campaign.client_id == client.id).order_by(Campaign.created_at.desc()))
    return result.scalars().all()

@router.post("/campaigns")
async def create_campaign(data: CampaignCreate, db: AsyncSession = Depends(get_db), current_user = Depends(require_client)):
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
        follow_up_days=data.follow_up_days,
        follow_up_template_id=data.follow_up_template_id
    )
    db.add(new_campaign)
    await db.commit()
    return {"status": "success", "campaign": new_campaign}

@router.delete("/campaigns/{campaign_id}")
async def delete_campaign(campaign_id: str, db: AsyncSession = Depends(get_db), current_user = Depends(require_client)):
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
    result = await db.execute(select(EmailLog.sent_at).where(
        EmailLog.client_id == client.id, 
        EmailLog.sent_at >= seven_days_ago
    ))
    logs = result.scalars().all()
    labels = []
    data = []
    for i in range(6, -1, -1):
        d = datetime.now(timezone.utc) - timedelta(days=i)
        labels.append(d.strftime("%Y-%m-%d"))
        data.append(0)
    
    for sent_at in logs:
        if not sent_at: continue
        date_str = sent_at.strftime("%Y-%m-%d")
        if date_str in labels:
            data[labels.index(date_str)] += 1
            
    return {"labels": labels, "data": data}

@router.post("/upload")
async def upload_image(file: UploadFile = File(...), current_user = Depends(require_client)):
    ext = file.filename.split(".")[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    file_path = os.path.join(uploads_dir, filename)
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    return {"url": f"/uploads/{filename}"}
