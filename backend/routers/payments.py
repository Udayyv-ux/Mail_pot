"""
Payment management API routes via Razorpay.
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from backend.database import get_db
from backend.middleware.auth_middleware import require_client
from backend.models.client import Client
from backend.models.plan import Plan
from backend.models.payment import Payment
from backend.models.app_settings import AppSetting
from backend.services.payment_service import create_order, verify_payment, process_webhook
from backend.config import settings

router = APIRouter(prefix="/api/payments", tags=["payments"])

async def get_client_record(user, db: AsyncSession):
    result = await db.execute(select(Client).where(Client.user_id == user.id))
    return result.scalar_one_or_none()

class OrderRequest(BaseModel):
    plan_id: str
    billing_cycle: str = "monthly"
    promo_code: str = None

@router.post("/create-order")
async def api_create_order(req: OrderRequest, db: AsyncSession = Depends(get_db), current_user = Depends(require_client)):
    client = await get_client_record(current_user, db)
    if not client:
        raise HTTPException(404, "Client not found")
        
    plan = await db.get(Plan, req.plan_id)
    if not plan:
        raise HTTPException(404, "Plan not found")
        
    if req.billing_cycle == "yearly":
        amount = round((plan.price_monthly * 12) * 0.75)  # 25% off
    elif req.billing_cycle == "half_yearly":
        amount = round((plan.price_monthly * 6) * 0.85)   # 15% off
    else:
        amount = plan.price_monthly
        
    if req.promo_code:
        from backend.models.promo_code import PromoCode
        pc_res = await db.execute(select(PromoCode).where(PromoCode.code == req.promo_code.upper()))
        pc = pc_res.scalar_one_or_none()
        if pc and pc.is_active and pc.uses < pc.max_uses:
            amount = round(amount * (1 - pc.discount_pct / 100))
            # Note: We should ideally increment uses only when payment is successful, 
            # but for simplicity we'll just check it here.

    if amount <= 0:
        raise HTTPException(400, "Invalid plan amount")
        
    try:
        receipt_id = f"plan_{plan.id}"[:40]
        order = await create_order(amount, db=db, receipt=receipt_id)
        
        # Fetch public key for frontend — admin saves it as RAZORPAY_KEY_ID (uppercase)
        result_key = await db.execute(select(AppSetting).where(AppSetting.key.in_(["razorpay_key_id", "RAZORPAY_KEY_ID"])))
        db_key = result_key.scalars().first()
        razorpay_key_id = db_key.value if db_key and db_key.value else settings.RAZORPAY_KEY_ID

        # Save payment record
        payment = Payment(
            client_id=client.id,
            plan_id=plan.id,
            amount=amount,
            billing_cycle=req.billing_cycle,
            razorpay_order_id=order["id"],
            status="created"
        )
        db.add(payment)
        await db.commit()
        
        return {"order_id": order["id"], "amount": amount, "currency": "INR", "razorpay_key_id": razorpay_key_id}
    except Exception as e:
        raise HTTPException(400, str(e))

class VerifyRequest(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str

@router.post("/verify")
async def api_verify_payment(req: VerifyRequest, db: AsyncSession = Depends(get_db), current_user = Depends(require_client)):
    is_valid = await verify_payment(req.razorpay_order_id, req.razorpay_payment_id, req.razorpay_signature, db=db)
    if is_valid:
        # Find payment record
        result = await db.execute(select(Payment).where(Payment.razorpay_order_id == req.razorpay_order_id))
        payment = result.scalar_one_or_none()
        
        if payment:
            payment.status = "paid"
            payment.razorpay_payment_id = req.razorpay_payment_id
            payment.razorpay_signature = req.razorpay_signature
            
            # Update client plan
            client = await db.get(Client, payment.client_id)
            if client:
                client.plan_id = payment.plan_id
                
                # Calculate expiration
                from datetime import datetime, timedelta, timezone
                if payment.billing_cycle == "yearly":
                    client.subscription_ends_at = datetime.now(timezone.utc) + timedelta(days=365)
                elif payment.billing_cycle == "half_yearly":
                    client.subscription_ends_at = datetime.now(timezone.utc) + timedelta(days=180)
                else:
                    client.subscription_ends_at = datetime.now(timezone.utc) + timedelta(days=30)
                    
                plan = await db.get(Plan, payment.plan_id)
                if plan:
                    client.daily_email_limit = plan.email_limit_daily
                    
            await db.commit()
            return {"status": "success"}
    
    raise HTTPException(400, "Payment verification failed")

@router.get("/history")
async def payment_history(db: AsyncSession = Depends(get_db), current_user = Depends(require_client)):
    client = await get_client_record(current_user, db)
    if not client:
        return []
        
    result = await db.execute(select(Payment).where(Payment.client_id == client.id).order_by(Payment.created_at.desc()))
    return result.scalars().all()

@router.post("/webhook")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Razorpay Webhooks."""
    body = await request.body()
    signature = request.headers.get("x-razorpay-signature", "")
    
    is_valid = await process_webhook(body.decode(), signature, db=db)
    if not is_valid:
        raise HTTPException(400, "Invalid signature")
        
    # Handle events like payment.captured, payment.failed here in production
    
    return {"status": "ok"}
