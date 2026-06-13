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
from backend.models.campaign import Campaign, EmailLog
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
    
    active_campaigns = await db.scalar(select(func.count(Campaign.id)).where(Campaign.client_id == client.id, Campaign.status == "running"))
    total_campaigns = await db.scalar(select(func.count(Campaign.id)).where(Campaign.client_id == client.id))
    
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


