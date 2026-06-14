"""
Super Admin API routes.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from pydantic import BaseModel
from typing import List, Optional
import aiosmtplib
from email.message import EmailMessage
import asyncio
from backend.config import settings

from backend.database import get_db
from backend.middleware.auth_middleware import require_admin
from backend.models.client import Client
from backend.models.user import User
from backend.models.plan import Plan
from backend.models.payment import Payment
from backend.models.app_settings import Policy, AppSetting, DemoRequest
from backend.models.campaign import Campaign, EmailLog

router = APIRouter(prefix="/api/admin", tags=["admin"])

# --- DASHBOARD ---
@router.get("/dashboard")
async def get_dashboard(db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    clients_count = await db.scalar(select(func.count(Client.id)))
    active_campaigns = await db.scalar(select(func.count(Campaign.id)).where(Campaign.status == "running"))
    emails_sent = await db.scalar(select(func.count(EmailLog.id)).where(EmailLog.status == "sent"))
    revenue = await db.scalar(select(func.sum(Payment.amount)).where(Payment.status == "paid")) or 0.0
    
    return {
        "total_clients": clients_count,
        "active_campaigns": active_campaigns,
        "total_emails_sent": emails_sent,
        "total_revenue": revenue
    }

# --- CLIENTS ---
@router.get("/clients")
async def list_clients(db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    result = await db.execute(select(Client).join(User))
    clients = result.scalars().all()
    return [{"id": c.id, "company_name": c.company_name, "status": c.status, "emails_sent_today": c.emails_sent_today} for c in clients]

@router.get("/clients/{id}")
async def get_client(id: str, db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    client = await db.get(Client, id)
    if not client:
        raise HTTPException(404, "Client not found")
    return client

@router.post("/clients/{id}/reset-usage")
async def reset_client_usage(id: str, db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    client = await db.get(Client, id)
    if not client:
        raise HTTPException(404, "Client not found")
    client.emails_sent_today = 0
    await db.commit()
    return {"status": "success"}

# --- PLANS ---
class PlanCreate(BaseModel):
    name: str
    description: str
    price_monthly: float
    price_yearly: float
    email_limit_daily: int
    features_json: str

@router.get("/plans")
async def list_plans(db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    result = await db.execute(select(Plan).order_by(Plan.sort_order))
    return result.scalars().all()

@router.post("/plans")
async def create_plan(plan: PlanCreate, db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    new_plan = Plan(**plan.model_dump())
    db.add(new_plan)
    await db.commit()
    return new_plan

@router.delete("/plans/{id}")
async def delete_plan(id: str, db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    plan = await db.get(Plan, id)
    if plan:
        await db.delete(plan)
        await db.commit()
    return {"status": "success"}

# --- SETTINGS ---
class SettingUpdate(BaseModel):
    key: str
    value: str

@router.get("/settings")
async def get_settings(db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    result = await db.execute(select(AppSetting))
    return result.scalars().all()

@router.put("/settings")
async def update_settings(settings: List[SettingUpdate], db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    for setting in settings:
        result = await db.execute(select(AppSetting).where(AppSetting.key == setting.key))
        db_setting = result.scalar_one_or_none()
        if db_setting:
            db_setting.value = setting.value
    await db.commit()
    return {"status": "success"}

# --- POLICIES (LEGAL CMS) ---
class PolicyCreateUpdate(BaseModel):
    title: str
    slug: str
    content_html: str
    is_active: bool = True

@router.get("/policies")
async def list_policies(db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    result = await db.execute(select(Policy).order_by(Policy.updated_at.desc()))
    return result.scalars().all()

@router.post("/policies")
async def save_policy(policy_data: PolicyCreateUpdate, db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    # Check if exists by slug
    result = await db.execute(select(Policy).where(Policy.slug == policy_data.slug))
    existing = result.scalar_one_or_none()
    
    if existing:
        existing.title = policy_data.title
        existing.content_html = policy_data.content_html
        existing.is_active = policy_data.is_active
    else:
        new_policy = Policy(**policy_data.model_dump())
        db.add(new_policy)
        
    await db.commit()
    return {"status": "success"}

@router.delete("/policies/{slug}")
async def delete_policy(slug: str, db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    result = await db.execute(select(Policy).where(Policy.slug == slug))
    policy = result.scalar_one_or_none()
    if policy:
        await db.delete(policy)
        await db.commit()
    return {"status": "success"}

# --- NOTIFICATIONS (ANNOUNCEMENTS) ---
class NotificationCreate(BaseModel):
    message: str
    type: str = "info"
    is_active: bool = True

@router.get("/notifications")
async def list_notifications(db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    from backend.models.app_settings import Notification
    result = await db.execute(select(Notification).order_by(Notification.created_at.desc()))
    return result.scalars().all()

@router.post("/notifications")
async def create_notification(notif: NotificationCreate, db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    from backend.models.app_settings import Notification
    new_notif = Notification(**notif.model_dump())
    db.add(new_notif)
    await db.commit()
    return {"status": "success"}

@router.delete("/notifications/{id}")
async def delete_notification(id: str, db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    from backend.models.app_settings import Notification
    notif = await db.get(Notification, id)
    if notif:
        await db.delete(notif)
        await db.commit()
    return {"status": "success"}

# --- ENGINE ---
@router.get("/engine/status")
async def engine_status(admin = Depends(require_admin)):
    from backend.services.queue_manager import queue_manager
    return {
        "is_running": queue_manager.is_running,
        "active_tenants": list(queue_manager.active_tenants)
    }

@router.post("/engine/pause")
async def pause_engine(admin = Depends(require_admin)):
    from backend.services.queue_manager import queue_manager
    await queue_manager.stop()
    return {"status": "paused"}

@router.post("/engine/resume")
async def resume_engine(admin = Depends(require_admin)):
    from backend.services.queue_manager import queue_manager
    await queue_manager.start_workers(5)
    return {"status": "running"}

# --- DEMO REQUESTS ---
@router.get("/demo-requests")
async def list_demo_requests(db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    result = await db.execute(select(DemoRequest).order_by(DemoRequest.created_at.desc()))
    return result.scalars().all()

class DemoEmailRequest(BaseModel):
    subject: str
    body_html: str

@router.post("/demo-requests/send-email")
async def send_demo_emails(req: DemoEmailRequest, db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    if not settings.DEFAULT_SMTP_EMAIL or not settings.DEFAULT_SMTP_PASSWORD:
        raise HTTPException(400, "Super Admin SMTP credentials are not set in .env")

    # Get all pending demo requests
    result = await db.execute(select(DemoRequest).where(DemoRequest.status == "pending"))
    requests = result.scalars().all()
    
    if not requests:
        return {"status": "success", "message": "No pending demo requests found.", "sent_count": 0}

    smtp_client = aiosmtplib.SMTP(
        hostname="smtp.gmail.com",
        port=587,
        use_tls=False,
        start_tls=True
    )
    
    try:
        await smtp_client.connect()
        await smtp_client.login(settings.DEFAULT_SMTP_EMAIL, settings.DEFAULT_SMTP_PASSWORD)
        
        sent_count = 0
        for dr in requests:
            msg = EmailMessage()
            msg["From"] = settings.DEFAULT_SMTP_EMAIL
            msg["To"] = dr.email
            msg["Subject"] = req.subject
            
            # Simple personalization
            personalized_body = req.body_html.replace("{name}", dr.name).replace("{company}", dr.company or "your company")
            msg.add_alternative(personalized_body, subtype="html")
            
            try:
                await smtp_client.send_message(msg)
                dr.status = "contacted"
                sent_count += 1
                await asyncio.sleep(1) # delay to prevent spam flagging
            except Exception as e:
                print(f"Failed to send demo email to {dr.email}: {e}")
                
        await db.commit()
    finally:
        try:
            await smtp_client.quit()
        except:
            pass
            
    return {"status": "success", "sent_count": sent_count}

