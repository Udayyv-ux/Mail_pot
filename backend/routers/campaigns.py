"""
Campaign management API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import datetime

from backend.database import get_db
from backend.middleware.auth_middleware import require_client
from backend.models.client import Client
from backend.models.campaign import Campaign, EmailLog
from backend.models.template import Template
from backend.services.queue_manager import queue_manager, EmailTask
from backend.services.sheets_service import get_sheet_data
from backend.utils.encryption import decrypt_value
from backend.config import settings

router = APIRouter(prefix="/api/client/campaigns", tags=["campaigns"])

async def get_client_record(user, db: AsyncSession):
    result = await db.execute(select(Client).where(Client.user_id == user.id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(404, "Client profile not found")
    return client

@router.get("/")
async def list_campaigns(db: AsyncSession = Depends(get_db), current_user = Depends(require_client)):
    client = await get_client_record(current_user, db)
    result = await db.execute(select(Campaign).where(Campaign.client_id == client.id).order_by(Campaign.created_at.desc()))
    return result.scalars().all()

class CampaignStart(BaseModel):
    name: str
    batch_size: int = 10

@router.post("/start")
async def start_campaign(data: CampaignStart, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db), current_user = Depends(require_client)):
    client = await get_client_record(current_user, db)
    
    if not client.google_sheet_id or not client.credentials_json:
        raise HTTPException(400, "Google Sheets not configured properly. Please setup ID and credentials.")
        
    # Get Templates
    result = await db.execute(select(Template).where(Template.client_id == client.id, Template.is_active == True))
    templates = result.scalars().all()
    if not templates:
        raise HTTPException(400, "No active templates found. Create at least one template first.")
        
    try:
        # Verify Sheet Connection
        _, records = await get_sheet_data(client.google_sheet_id, client.credentials_json)
    except Exception as e:
        raise HTTPException(400, f"Failed to connect to Google Sheet: {str(e)}")
        
    total_leads = len(records) - 1 if len(records) > 0 else 0
    
    # Create Campaign Record
    campaign = Campaign(
        client_id=client.id,
        name=data.name,
        sheet_id=client.google_sheet_id,
        status="running",
        total_leads=total_leads,
        batch_size=data.batch_size,
        started_at=datetime.datetime.utcnow()
    )
    db.add(campaign)
    await db.commit()
    
    # Register client in QueueManager
    queue_manager.register_tenant(client.id, daily_limit=client.daily_email_limit)
    queue_manager.resume_campaign(campaign.id)
    
    smtp_config = {
        "email": client.smtp_email,
        "password": decrypt_value(client.smtp_password_enc) if client.smtp_password_enc else None,
        "host": client.smtp_host,
        "port": client.smtp_port
    }
    
    groq_key = decrypt_value(client.groq_api_key_enc) if client.groq_api_key_enc else settings.GROQ_API_KEY
    
    # Queue up the leads
    emails_queued = 0
    # Assuming standard format: Name, Email, Inquiry, Category, Status
    for i, row in list(enumerate(records[1:], start=2)):
        if emails_queued >= data.batch_size:
            break
            
        name = row[0] if len(row) > 0 else ""
        email = row[1] if len(row) > 1 else ""
        inquiry = row[2] if len(row) > 2 else ""
        status = row[4] if len(row) > 4 else ""
        
        if email.strip() and inquiry.strip() and status != "Sent":
            task = EmailTask(
                campaign_id=campaign.id,
                client_id=client.id,
                to_email=email,
                name=name,
                inquiry=inquiry,
                row_index=i,
                templates=templates,
                smtp_config=smtp_config,
                groq_key=groq_key,
                sheet_id=client.google_sheet_id,
                credentials_json=client.credentials_json
            )
            # Enqueue to background async
            background_tasks.add_task(queue_manager.enqueue, task)
            emails_queued += 1

    return {"status": "success", "campaign_id": campaign.id, "emails_queued": emails_queued}

@router.post("/{id}/pause")
async def pause_campaign(id: str, db: AsyncSession = Depends(get_db), current_user = Depends(require_client)):
    client = await get_client_record(current_user, db)
    campaign = await db.get(Campaign, id)
    if campaign and campaign.client_id == client.id:
        campaign.status = "paused"
        await db.commit()
        queue_manager.pause_campaign(id)
    return {"status": "paused"}

@router.post("/{id}/resume")
async def resume_campaign(id: str, db: AsyncSession = Depends(get_db), current_user = Depends(require_client)):
    client = await get_client_record(current_user, db)
    campaign = await db.get(Campaign, id)
    if campaign and campaign.client_id == client.id:
        campaign.status = "running"
        await db.commit()
        queue_manager.resume_campaign(id)
    return {"status": "running"}

@router.get("/{id}/logs")
async def get_campaign_logs(id: str, db: AsyncSession = Depends(get_db), current_user = Depends(require_client)):
    client = await get_client_record(current_user, db)
    campaign = await db.get(Campaign, id)
    if not campaign or campaign.client_id != client.id:
        raise HTTPException(404, "Campaign not found")
        
    result = await db.execute(select(EmailLog).where(EmailLog.campaign_id == id).order_by(EmailLog.sent_at.desc()))
    return result.scalars().all()
