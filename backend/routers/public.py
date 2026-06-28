"""
Public API routes for landing page (no auth required).
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from backend.database import get_db
from backend.models.plan import Plan
from backend.models.app_settings import Policy, AppSetting, DemoRequest
from backend.models.appointment import Appointment
from backend.models.email_log import EmailLog
import uuid
from datetime import datetime, timedelta, timezone

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
async def send_demo_emails_async_task(data: DemoSubmit, admin_email: str):
    import base64
    from email.message import EmailMessage
    import httpx
    from sqlalchemy import select
    from backend.database import SessionLocal
    from backend.models.user import User
    from backend.services.email_engine import refresh_google_token
    from backend.config import settings

    if not admin_email:
        return

    meet_link = "https://meet.google.com/ais-cmqc-dci" # User provided link

    async with SessionLocal() as db:
        # Find Super Admin user to get OAuth tokens
        res = await db.execute(select(User).where(User.email == admin_email))
        admin_user = res.scalar_one_or_none()
        if not admin_user or not admin_user.google_access_token:
            print("Demo emails failed: Super Admin not found or has no Google tokens.")
            return

        # Ensure token is fresh
        access_token = await refresh_google_token(admin_user, db)
        await db.commit()

    async def send_via_gmail(to_email: str, subject: str, text_body: str):
        msg = EmailMessage()
        msg['To'] = to_email
        msg['From'] = admin_email
        msg['Subject'] = subject
        msg.set_content(text_body)
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode('utf-8')
        
        async with httpx.AsyncClient() as http_client:
            resp = await http_client.post(
                "https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
                headers={"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"},
                json={"raw": raw},
                timeout=15.0
            )
            if resp.status_code != 200:
                print(f"Failed to send via Gmail API to {to_email}: {resp.text}")

    # 1. Admin Email
    admin_body = f"New Demo Request:\nName: {data.name}\nEmail: {data.email}\nCompany: {data.company}\nScheduled: {data.scheduled_time}\nType: {data.inquiry_type}\nMessage: {data.message}"
    await send_via_gmail(admin_email, f"New Demo Request: {data.name}", admin_body)

    # 2. User Email
    user_body = f"Hi {data.name},\n\nYour demo is confirmed for: {data.scheduled_time}.\n\nPlease join us at that time using this Google Meet link:\n{meet_link}\n\nWe look forward to speaking with you!\n\nBest,\nThe Team"
    await send_via_gmail(data.email, "Your Demo is Confirmed!", user_body)

from fastapi import BackgroundTasks

@router.post("/demo-request")
async def submit_demo(data: DemoSubmit, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    from backend.config import settings
    demo = DemoRequest(**data.model_dump())
    db.add(demo)
    await db.commit()
    
    if data.scheduled_time:
        admin_email = settings.SUPER_ADMIN_EMAIL
        background_tasks.add_task(send_demo_emails_async_task, data, admin_email)
        
    return {"status": "success"}

@router.get("/settings")
async def get_public_settings(db: AsyncSession = Depends(get_db)):
    # Only return branding and landing categories
    result = await db.execute(select(AppSetting).where(AppSetting.category.in_(["branding", "landing"])))
    settings_list = result.scalars().all()
    
    # Format as key-value dict
    return {s.key: s.value for s in settings_list}

class BookAppointmentReq(BaseModel):
    name: str
    email: str
    date: str
    time_slot: str

@router.get("/appointments/slots")
async def get_available_slots(date: str, db: AsyncSession = Depends(get_db)):
    # Standard slots 9 AM to 5 PM, 30 min intervals
    all_slots = [
        "09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM",
        "11:00 AM", "11:30 AM", "12:00 PM", "12:30 PM",
        "01:00 PM", "01:30 PM", "02:00 PM", "02:30 PM",
        "03:00 PM", "03:30 PM", "04:00 PM", "04:30 PM", "05:00 PM"
    ]
    
    # Query database for booked slots on this date
    result = await db.execute(select(Appointment.time_slot).where(Appointment.date == date, Appointment.status.in_(["pending", "confirmed"])))
    booked_slots = result.scalars().all()
    
    available_slots = [slot for slot in all_slots if slot not in booked_slots]
    return {"date": date, "available_slots": available_slots}

@router.post("/appointments/book")
async def book_appointment(data: BookAppointmentReq, db: AsyncSession = Depends(get_db)):
    # Verify slot availability
    result = await db.execute(select(Appointment).where(Appointment.date == data.date, Appointment.time_slot == data.time_slot, Appointment.status.in_(["pending", "confirmed"])))
    if result.scalars().first():
        raise HTTPException(400, "This time slot is already booked. Please select another time.")

    appointment = Appointment(
        id=str(uuid.uuid4()),
        name=data.name,
        email=data.email,
        date=data.date,
        time_slot=data.time_slot,
        status="confirmed"
    )
    db.add(appointment)
    await db.commit()

    # Trigger async email notification
    from backend.services.email_engine import send_appointment_emails_async
    import asyncio
    asyncio.create_task(send_appointment_emails_async(data.name, data.email, data.date, data.time_slot))

    return {"status": "success", "message": "Appointment booked successfully!"}

from typing import Optional

class NewsletterReq(BaseModel):
    email: str
    mobile: str

@router.post("/newsletter/subscribe")
async def subscribe_newsletter(data: NewsletterReq, db: AsyncSession = Depends(get_db)):
    from backend.models.newsletter import NewsletterSubscriber
    
    # Check if already subscribed
    result = await db.execute(select(NewsletterSubscriber).where(NewsletterSubscriber.email == data.email))
    if result.scalars().first():
        return {"status": "success", "message": "Already subscribed."}

    sub = NewsletterSubscriber(
        id=str(uuid.uuid4()),
        email=data.email,
        mobile=data.mobile
    )
    db.add(sub)
    await db.commit()
    return {"status": "success", "message": "Subscribed successfully!"}

class WATestReq(BaseModel):
    phone: str
    template_name: str = "hello_world"

@router.post("/test-wa")
async def test_wa(data: WATestReq, db: AsyncSession = Depends(get_db)):
    from backend.models.client import Client
    from backend.services.whatsapp_service import send_whatsapp_message
    
    # Get the first active client (assuming single-tenant or just grabbing the user's config)
    res = await db.execute(select(Client).where(Client.is_active == True))
    client = res.scalars().first()
    
    if not client:
        return {"status": "error", "message": "No active client found to fetch WhatsApp credentials from."}
    
    try:
        msg_id = await send_whatsapp_message(
            client_id=client.id,
            to_phone=data.phone,
            template_name=data.template_name,
            db=db
        )
        return {"status": "success", "message": "Message sent!", "message_id": msg_id}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/track/open/{log_id}")
async def track_email_open(log_id: str, db: AsyncSession = Depends(get_db)):
    pixel = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
    try:
        log = await db.get(EmailLog, log_id)
        if log and not log.opened:
            log.opened = True
            log.opened_at = datetime.now(timezone.utc)
            await db.commit()
    except Exception:
        pass
    return Response(content=pixel, media_type="image/gif")
