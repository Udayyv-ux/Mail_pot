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
from backend.models.email_log import EmailLog
from datetime import datetime, timedelta, timezone
from fastapi import UploadFile, File
import base64

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/email-logs")
async def get_global_email_logs(db: AsyncSession = Depends(get_db), admin = Depends(require_admin), limit: int = 50):
    result = await db.execute(
        select(EmailLog)
        .order_by(EmailLog.sent_at.desc())
        .limit(limit)
    )
    logs = result.scalars().all()
    return [{
        "id": log.id,
        "client_id": log.client_id,
        "recipient_email": log.recipient_email,
        "status": log.status,
        "sent_at": log.sent_at.isoformat() if log.sent_at else None,
        "error_message": log.error_message
    } for log in logs]

# --- DASHBOARD ---

from backend.middleware.auth_middleware import create_access_token

@router.post("/impersonate/{user_id}")
async def impersonate_user(user_id: str, db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    token = create_access_token({"sub": user.id})
    return {"access_token": token, "message": f"Impersonating {user.name}"}

@router.get("/dashboard")
async def get_dashboard(db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    clients_count = await db.scalar(select(func.count(Client.id)))
    active_campaigns = 0
    emails_sent = await db.scalar(select(func.count(EmailLog.id)).where(EmailLog.status == "sent"))
    revenue = await db.scalar(select(func.sum(Payment.amount)).where(Payment.status == "paid")) or 0.0
    
    return {
        "total_clients": clients_count,
        "active_campaigns": active_campaigns,
        "total_emails_sent": emails_sent,
        "total_revenue": revenue
    }

@router.get("/analytics/chart")
async def get_admin_chart(db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    result = await db.execute(select(EmailLog.sent_at).where(
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

# --- CLIENTS ---
@router.get("/clients")
async def list_clients(db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    # Need to join User and Plan to get email and plan name
    from sqlalchemy.orm import selectinload
    result = await db.execute(select(Client).options(selectinload(Client.user), selectinload(Client.plan)))
    clients = result.scalars().all()
    return [{
        "id": c.id, 
        "user_id": c.user_id,
        "email": c.user.email if c.user else "N/A",
        "company_name": c.company_name, 
        "plan": c.plan.name if c.plan else "Free",
        "status": c.status, 
        "emails_sent_today": c.emails_sent_today
    } for c in clients]

@router.get("/clients/{id}")
async def get_client(id: str, db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    from sqlalchemy.orm import selectinload
    result = await db.execute(select(Client).options(selectinload(Client.user), selectinload(Client.plan)).where(Client.id == id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(404, "Client not found")
    
    return {
        "id": client.id,
        "company_name": client.company_name,
        "status": client.status,
        "daily_email_limit": client.daily_email_limit,
        "emails_sent_today": client.emails_sent_today,
        "google_sheet_id": client.google_sheet_id,
        "target_columns": client.target_columns,
        "status_column": client.status_column,
        "smtp_host": client.smtp_host,
        "smtp_port": client.smtp_port,
        "smtp_email": client.smtp_email,
        "groq_api_key_enc": client.groq_api_key_enc,
        "features_json": client.features_json,
        "user": {"email": client.user.email} if client.user else None,
        "plan": {"name": client.plan.name} if client.plan else None
    }

@router.post("/clients/{id}/reset-usage")
async def reset_client_usage(id: str, db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    client = await db.get(Client, id)
    if not client:
        raise HTTPException(404, "Client not found")
    client.emails_sent_today = 0
    await db.commit()
    return {"status": "success"}

class ClientFeaturesUpdate(BaseModel):
    ai_matcher: bool
    whitelabel: bool

@router.put("/clients/{id}/features")
async def update_client_features(id: str, features: ClientFeaturesUpdate, db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    import json
    client = await db.get(Client, id)
    if not client:
        raise HTTPException(404, "Client not found")
    client.features_json = json.dumps(features.model_dump())
    await db.commit()
    return {"status": "success"}

# --- PLANS ---
class PlanCreate(BaseModel):
    name: str
    description: str
    price_monthly: float
    price_half_yearly: float
    price_yearly: float
    email_limit_daily: int
    campaign_limit: int
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

@router.put("/plans/{id}")
async def update_plan(id: str, plan_update: PlanCreate, db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    plan = await db.get(Plan, id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    for key, value in plan_update.model_dump().items():
        setattr(plan, key, value)
        
    await db.commit()
    return plan

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
            if setting.key.startswith("LANDING_"):
                db_setting.category = "landing"
        else:
            cat = "landing" if setting.key.startswith("LANDING_") else "general"
            new_setting = AppSetting(key=setting.key, value=setting.value, category=cat)
            db.add(new_setting)
    await db.commit()
    return {"status": "success"}

@router.post("/settings/logo")
async def upload_logo(file: UploadFile = File(...), db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    contents = await file.read()
    b64 = base64.b64encode(contents).decode("utf-8")
    mime = file.content_type if file.content_type else "image/png"
    data_uri = f"data:{mime};base64,{b64}"

    # Upsert the SITE_LOGO directly
    result = await db.execute(select(AppSetting).where(AppSetting.key == "SITE_LOGO"))
    setting = result.scalar_one_or_none()
    if not setting:
        setting = AppSetting(key="SITE_LOGO", category="general", value=data_uri)
        db.add(setting)
    else:
        setting.value = data_uri
        
    await db.commit()
    return {"status": "success", "url": "/api/logo"}

# --- POLICIES (LEGAL CMS) ---
class PolicyCreateUpdate(BaseModel):
    title: str
    slug: str
    icon: str = "📜"
    description: str = ""
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
        existing.icon = policy_data.icon
        existing.description = policy_data.description
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
    return {"is_running": True, "active_tenants": []}

@router.post("/engine/pause")
async def pause_engine(admin = Depends(require_admin)):
    return {"status": "paused"}

@router.post("/engine/resume")
async def resume_engine(admin = Depends(require_admin)):
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

@router.get("/revenue")
async def get_revenue_metrics(db: AsyncSession = Depends(get_db), current_admin = Depends(require_admin)):
    from backend.models.client import Client
    from backend.models.plan import Plan
    from sqlalchemy.orm import selectinload
    
    # Active clients with their plans
    res = await db.execute(select(Client).options(selectinload(Client.plan)).where(Client.status == "active"))
    clients = res.scalars().all()
    
    mrr = 0
    active_subscriptions = 0
    
    for c in clients:
        if c.plan and c.plan.price_monthly > 0:
            mrr += c.plan.price_monthly
            active_subscriptions += 1
            
    # Total revenue ever
    from backend.models.payment import Payment
    pay_res = await db.execute(select(func.sum(Payment.amount)).where(Payment.status == "paid"))
    total_revenue = pay_res.scalar() or 0
    
    return {
        "mrr": mrr,
        "active_subscriptions": active_subscriptions,
        "total_revenue": total_revenue
    }

from pydantic import BaseModel
class PromoCodeCreate(BaseModel):
    code: str
    discount_pct: int
    max_uses: int = 100
    is_active: bool = True

@router.get("/promo-codes")
async def get_promo_codes(db: AsyncSession = Depends(get_db), current_admin = Depends(require_admin)):
    from backend.models.promo_code import PromoCode
    res = await db.execute(select(PromoCode).order_by(PromoCode.created_at.desc()))
    return res.scalars().all()

@router.post("/promo-codes")
async def create_promo_code(promo: PromoCodeCreate, db: AsyncSession = Depends(get_db), current_admin = Depends(require_admin)):
    from backend.models.promo_code import PromoCode
    pc = PromoCode(**promo.model_dump())
    db.add(pc)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(400, "Promo code might already exist")
    return pc

@router.delete("/promo-codes/{id}")
async def delete_promo_code(id: str, db: AsyncSession = Depends(get_db), current_admin = Depends(require_admin)):
    from backend.models.promo_code import PromoCode
    pc = await db.get(PromoCode, id)
    if not pc:
        raise HTTPException(404, "Not found")
    await db.delete(pc)
    await db.commit()
    return {"status": "success"}

class AdminEmailRequest(BaseModel):
    target_email: str
    subject: str
    body_html: str

@router.post("/send-email")
async def send_admin_email(req: AdminEmailRequest, db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    if not settings.DEFAULT_SMTP_EMAIL or not settings.DEFAULT_SMTP_PASSWORD:
        raise HTTPException(400, "Super Admin SMTP credentials are not set in .env")
        
    targets = []
    if req.target_email == "all_users":
        res = await db.execute(select(Client))
        for c in res.scalars().all():
            if c.email:
                targets.append(c.email)
    else:
        targets = [req.target_email]

    if not targets:
        return {"status": "success", "sent": 0, "message": "No targets found."}

    smtp_client = aiosmtplib.SMTP(
        hostname="smtp.gmail.com",
        port=587,
        use_tls=False,
        start_tls=True
    )
    
    try:
        await smtp_client.connect()
        await smtp_client.login(settings.DEFAULT_SMTP_EMAIL, settings.DEFAULT_SMTP_PASSWORD)
        
        sent = 0
        for email in targets:
            msg = EmailMessage()
            msg["From"] = settings.DEFAULT_SMTP_EMAIL
            msg["To"] = email
            msg["Subject"] = req.subject
            msg.set_content("Please view this email in an HTML-compatible client.")
            msg.add_alternative(req.body_html, subtype='html')
            try:
                await smtp_client.send_message(msg)
                sent += 1
            except Exception:
                pass
                
        await smtp_client.quit()
        return {"status": "success", "sent": sent}
    except Exception as e:
        raise HTTPException(500, f"SMTP Error: {str(e)}")
