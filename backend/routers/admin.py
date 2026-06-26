"""
Super Admin API routes.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, update
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
from backend.models.app_settings import Policy, AppSetting, DemoRequest, Notification
from backend.models.promo_code import PromoCode
from backend.models.appointment import Appointment
from backend.middleware.auth_middleware import require_admin
from backend.services.whatsapp_service import send_whatsapp_message, timedelta, timezone
from backend.models.email_log import EmailLog
from backend.models.campaign import Campaign
from datetime import datetime, timedelta, timezone
from fastapi import UploadFile, File
import base64

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/email-logs")
async def get_global_email_logs(db: AsyncSession = Depends(get_db), admin = Depends(require_admin), limit: int = 50):
    result = await db.execute(
        select(EmailLog)
        .order_by(EmailLog.sent_at.desc().nulls_last())
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
        "emails_sent_today": c.emails_sent_today,
        "is_demo": getattr(c, "is_demo", False),
        "trial_ends_at": c.trial_ends_at.isoformat() if c.trial_ends_at else None
    } for c in clients]

@router.get("/clients/{id}")
async def get_client(id: str, db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    from sqlalchemy.orm import selectinload
    result = await db.execute(select(Client).options(selectinload(Client.user), selectinload(Client.plan)).where(Client.id == id))
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(404, "Client not found")
    
    # Fetch insights
    total_emails_sent = await db.scalar(select(func.count(EmailLog.id)).where(EmailLog.client_id == id))
    total_campaigns = await db.scalar(select(func.count(Campaign.id)).where(Campaign.client_id == id))
    active_campaigns = await db.scalar(select(func.count(Campaign.id)).where(Campaign.client_id == id, Campaign.is_active == True))
    
    return {
        "id": client.id,
        "company_name": client.company_name,
        "status": client.status,
        "daily_email_limit": client.daily_email_limit,
        "emails_sent_today": client.emails_sent_today,
        "user": {"email": client.user.email} if client.user else None,
        "plan": {"name": client.plan.name} if client.plan else None,
        "insights": {
            "total_emails_sent": total_emails_sent or 0,
            "total_campaigns": total_campaigns or 0,
            "active_campaigns": active_campaigns or 0,
            "created_at": client.created_at.isoformat() if client.created_at else None
        }
    }

@router.post("/clients/{id}/reset-usage")
async def reset_client_usage(id: str, db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    client = await db.get(Client, id)
    if not client:
        raise HTTPException(404, "Client not found")
    client.emails_sent_today = 0
    await db.commit()
    return {"status": "success"}

class DemoStatusUpdate(BaseModel):
    is_demo: bool

@router.put("/clients/{id}/demo-status")
async def update_demo_status(id: str, status: DemoStatusUpdate, db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    client = await db.get(Client, id)
    if not client:
        raise HTTPException(404, "Client not found")
    client.is_demo = status.is_demo
    await db.commit()
    return {"status": "success", "is_demo": client.is_demo}

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
    has_ai_templates: bool = False

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
    from backend.services.email_engine import send_email_via_gmail_api, refresh_google_token
    
    # Get all pending demo requests
    result = await db.execute(select(DemoRequest).where(DemoRequest.status == "pending"))
    requests = result.scalars().all()
    
    if not requests:
        return {"status": "success", "message": "No pending demo requests found.", "sent_count": 0}

    # Use the admin's OAuth token
    admin_user = await db.get(User, admin.id) if hasattr(admin, 'id') else admin
    access_token = await refresh_google_token(admin_user, db)
    if not access_token:
        raise HTTPException(400, "Super Admin Google OAuth token is missing or expired. Please re-login.")

    sent_count = 0
    for dr in requests:
        class PersonalizedTemplate:
            subject = req.subject
            body_html = req.body_html.replace("{name}", dr.name).replace("{company}", dr.company or "your company")
            banner_url = None

        success, err = await send_email_via_gmail_api(dr.email, dr.name, PersonalizedTemplate(), access_token)
        if success:
            dr.status = "contacted"
            sent_count += 1
            await asyncio.sleep(1) # delay
        else:
            print(f"Failed to send demo email to {dr.email}: {err}")
            
    await db.commit()
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
    target_emails: list[str] = []
    subject: str
    body_html: str

@router.post("/send-email")
async def send_admin_email(req: AdminEmailRequest, db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    from backend.services.email_engine import send_email_via_gmail_api, refresh_google_token
    
    targets = []
    if req.target_email == "all_users":
        from sqlalchemy.orm import selectinload
        res = await db.execute(select(Client).options(selectinload(Client.user)).where(Client.status == "active"))
        for c in res.scalars().all():
            if c.user and c.user.email:
                targets.append((c.user.email, getattr(c, "company_name", "User")))
    elif req.target_email == "multiple":
        # New multi-select logic
        for email in req.target_emails:
            targets.append((email, "User"))
    else:
        targets = [(req.target_email, "User")]

    if not targets:
        return {"status": "success", "sent": 0, "message": "No targets found."}

    admin_user = await db.get(User, admin.id) if hasattr(admin, 'id') else admin
    access_token = await refresh_google_token(admin_user, db)
    if not access_token:
        raise HTTPException(400, "Super Admin Google OAuth token is missing or expired. Please re-login.")

    class DummyTemplate:
        subject = req.subject
        body_html = req.body_html
        banner_url = None

    sent = 0
    for email, name in targets:
        success, err = await send_email_via_gmail_api(email, name, DummyTemplate(), access_token)
        if success:
            sent += 1
            await db.execute(update(DemoRequest).where(DemoRequest.email == email).values(status="contacted"))
    await db.commit()
            
    return {"status": "success", "sent": sent}

class AdminAIGenerateRequest(BaseModel):
    prompt: str

@router.post('/generate-email')
async def admin_generate_email(req: AdminAIGenerateRequest, db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    from groq import AsyncGroq
    from backend.config import settings
    import json
    
    system_prompt = (
        "You are an expert email copywriter. The user will give you a brief prompt about what to say to a user. " 
        "Write a highly professional, concise email. Return ONLY a JSON object with two keys: 'subject' and 'body_html'. " 
        "The 'body_html' should use standard HTML formatting (paragraphs, bold, etc)." 
    )
    
    try:
        client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.prompt}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- WHATSAPP ENGINE ---
import httpx

@router.get("/whatsapp/templates")
async def get_admin_whatsapp_templates(db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    from backend.models.app_settings import AppSetting
    result = await db.execute(select(AppSetting).where(AppSetting.key.in_(
        ["WHATSAPP_ACCESS_TOKEN", "WHATSAPP_BUSINESS_ACCOUNT_ID"]
    )))
    settings_dict = {s.key: s.value for s in result.scalars().all()}
    
    access_token = settings_dict.get("WHATSAPP_ACCESS_TOKEN")
    waba_id = settings_dict.get("WHATSAPP_BUSINESS_ACCOUNT_ID")
    
    if not access_token or not waba_id:
        raise HTTPException(status_code=400, detail="Global WhatsApp API credentials not configured in App Settings.")

    url = f"https://graph.facebook.com/v23.0/{waba_id}/message_templates"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)

class AdminWhatsappBroadcastRequest(BaseModel):
    template_name: str

@router.post("/broadcast-whatsapp")
async def broadcast_whatsapp(req: AdminWhatsappBroadcastRequest, db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    from backend.services.whatsapp_service import send_whatsapp_message
    from backend.models.app_settings import AppSetting
    
    result = await db.execute(select(AppSetting).where(AppSetting.key.in_(
        ["WHATSAPP_ACCESS_TOKEN", "WHATSAPP_PHONE_NUMBER_ID"]
    )))
    settings_dict = {s.key: s.value for s in result.scalars().all()}
    
    access_token = settings_dict.get("WHATSAPP_ACCESS_TOKEN")
    phone_id = settings_dict.get("WHATSAPP_PHONE_NUMBER_ID")
    
    if not access_token or not phone_id:
        raise HTTPException(status_code=400, detail="Global WhatsApp API credentials not configured.")
        
    res = await db.execute(select(Client).where(Client.status == "active"))
    clients = res.scalars().all()
    
    sent_count = 0
    errors = []
    
    for c in clients:
        phone = getattr(c, "phone", None)
        if phone:
            success, err = await send_whatsapp_message(
                phone=phone,
                template_name=req.template_name,
                access_token=access_token,
                phone_number_id=phone_id
            )
            if success:
                sent_count += 1
            else:
                errors.append(f"{phone}: {err}")
                
    return {
        "status": "success",
        "sent": sent_count,
        "errors": errors
    }

@router.get("/appointments")
async def list_appointments(db: AsyncSession = Depends(get_db), admin = Depends(require_admin)):
    result = await db.execute(select(Appointment).order_by(Appointment.date.desc(), Appointment.time_slot.desc()))
    return result.scalars().all()

