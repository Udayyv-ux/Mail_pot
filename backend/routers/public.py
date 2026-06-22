"""
Public API routes for landing page (no auth required).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from backend.database import get_db
from backend.models.plan import Plan
from backend.models.app_settings import Policy, AppSetting, DemoRequest

router = APIRouter(prefix="/api/public", tags=["public"])

@router.get("/plans")
async def get_active_plans(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Plan).where(Plan.is_active == True).order_by(Plan.price_monthly.asc()))
    return result.scalars().all()

@router.get("/policies")
async def list_policies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Policy).where(Policy.is_active == True))
    return result.scalars().all()

@router.get("/policies/{slug}")
async def get_policy(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Policy).where(Policy.slug == slug, Policy.is_active == True))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(404, "Policy not found")
    return policy

class DemoSubmit(BaseModel):
    name: str
    email: str
    company: str = ""
    phone: str = ""
    message: str = ""
    inquiry_type: str = "Demo"
    scheduled_time: str = None

def send_demo_emails_sync(data: DemoSubmit):
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from backend.config import settings

    if not settings.DEFAULT_SMTP_EMAIL or not settings.DEFAULT_SMTP_PASSWORD:
        return

    # Hardcoded permanent Google Meet link (can be moved to settings later)
    meet_link = "https://meet.google.com/qxc-rghw-vyt" # Example link

    # 1. Email to Admin
    msg_admin = MIMEMultipart()
    msg_admin["From"] = f"MailPilot <{settings.DEFAULT_SMTP_EMAIL}>"
    msg_admin["To"] = settings.SUPER_ADMIN_EMAIL if settings.SUPER_ADMIN_EMAIL else settings.DEFAULT_SMTP_EMAIL
    msg_admin["Subject"] = f"New Demo Request: {data.name}"
    
    admin_body = f"""
    New Demo Request:
    Name: {data.name}
    Email: {data.email}
    Company: {data.company}
    Scheduled Time: {data.scheduled_time}
    Type: {data.inquiry_type}
    Message: {data.message}
    """
    msg_admin.attach(MIMEText(admin_body, "plain"))

    # 2. Email to User
    msg_user = MIMEMultipart()
    msg_user["From"] = f"MailPilot <{settings.DEFAULT_SMTP_EMAIL}>"
    msg_user["To"] = data.email
    msg_user["Subject"] = "Your Demo is Confirmed!"
    
    user_body = f"""
    Hi {data.name},
    
    Your demo is confirmed for: {data.scheduled_time}.
    
    Please join us at that time using this Google Meet link:
    {meet_link}
    
    We look forward to speaking with you!
    
    Best,
    The Team
    """
    msg_user.attach(MIMEText(user_body, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(settings.DEFAULT_SMTP_EMAIL, settings.DEFAULT_SMTP_PASSWORD)
            server.send_message(msg_admin)
            server.send_message(msg_user)
    except Exception as e:
        print(f"Failed to send demo emails: {e}")

from fastapi import BackgroundTasks

@router.post("/demo-request")
async def submit_demo(data: DemoSubmit, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    demo = DemoRequest(**data.model_dump())
    db.add(demo)
    await db.commit()
    
    if data.scheduled_time:
        background_tasks.add_task(send_demo_emails_sync, data)
        
    return {"status": "success"}

@router.get("/settings")
async def get_public_settings(db: AsyncSession = Depends(get_db)):
    # Only return branding and landing categories
    result = await db.execute(select(AppSetting).where(AppSetting.category.in_(["branding", "landing"])))
    settings_list = result.scalars().all()
    
    # Format as key-value dict
    return {s.key: s.value for s in settings_list}
