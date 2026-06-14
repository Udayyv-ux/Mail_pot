"""
Client portal API routes.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from backend.database import get_db
from backend.middleware.auth_middleware import require_client
from backend.models.client import Client
from backend.models.email_log import EmailLog
from datetime import datetime, timedelta, timezone
from fastapi import UploadFile, File, BackgroundTasks
import os
import uuid
from backend.services.email_engine import run_blast_engine
from backend.utils.encryption import encrypt_value

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
    
    active_campaigns = 0
    total_campaigns = 0
    
    return {
        "emails_sent_today": client.emails_sent_today,
        "daily_limit": client.daily_email_limit,
        "active_campaigns": active_campaigns,
        "total_campaigns": total_campaigns,
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
            
    return {
        "company_name": client.company_name,
        "smtp_email": client.smtp_email,
        "smtp_host": client.smtp_host,
        "smtp_port": client.smtp_port,
        "google_sheet_id": client.google_sheet_id,
        "has_groq_key": bool(client.groq_api_key_enc),
        "service_account_email": service_email
    }

class ProfileUpdate(BaseModel):
    company_name: str = None
    smtp_email: str = None
    smtp_password: str = None
    groq_api_key: str = None

@router.put("/profile")
async def update_profile(data: ProfileUpdate, db: AsyncSession = Depends(get_db), current_user = Depends(require_client)):
    client = await get_client_profile(current_user, db)
    
    if data.company_name:
        client.company_name = data.company_name
    if data.smtp_email:
        client.smtp_email = data.smtp_email
    if data.smtp_password:
        client.smtp_password_enc = encrypt_value(data.smtp_password)
    if data.groq_api_key:
        client.groq_api_key_enc = encrypt_value(data.groq_api_key)
        
    await db.commit()
    return {"status": "success"}

class SheetUpdate(BaseModel):
    sheet_url_or_id: str

@router.put("/sheet")
async def update_sheet(data: SheetUpdate, db: AsyncSession = Depends(get_db), current_user = Depends(require_client)):
    import re
    client = await get_client_profile(current_user, db)
    
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', data.sheet_url_or_id)
    sheet_id = match.group(1) if match else data.sheet_url_or_id.strip()
    
    client.google_sheet_id = sheet_id
    await db.commit()
    return {"status": "success", "sheet_id": sheet_id}

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

class BlastRequest(BaseModel):
    batch_size: int = 10
    delay_seconds: int = 3

@router.post("/blast")
async def trigger_blast(req: BlastRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db), current_user = Depends(require_client)):
    client = await get_client_profile(current_user, db)
    background_tasks.add_task(run_blast_engine, client.id, req.batch_size, req.delay_seconds)
    return {"status": "success", "message": "Blast engine started"}
