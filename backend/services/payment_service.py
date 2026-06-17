"""
Razorpay integration service.
"""
import razorpay
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from backend.config import settings
from backend.models.app_settings import AppSetting

async def _get_client(db: AsyncSession):
    # Try DB first — admin saves with uppercase keys: RAZORPAY_KEY_ID, RAZORPAY_SECRET
    result_id = await db.execute(select(AppSetting).where(AppSetting.key.in_(["razorpay_key_id", "RAZORPAY_KEY_ID"])))
    result_secret = await db.execute(select(AppSetting).where(AppSetting.key.in_(["razorpay_key_secret", "RAZORPAY_SECRET", "razorpay_key_secret"])))
    
    db_id = result_id.scalars().first()
    db_secret = result_secret.scalars().first()
    
    key_id = db_id.value if db_id and db_id.value else settings.RAZORPAY_KEY_ID
    key_secret = db_secret.value if db_secret and db_secret.value else settings.RAZORPAY_KEY_SECRET

    if not key_id or not key_secret or key_id.startswith("rzp_test_xxx"):
        raise HTTPException(status_code=500, detail="Razorpay credentials not configured. Please set them in Admin → Settings.")
    return razorpay.Client(auth=(key_id, key_secret))

async def create_order(amount: float, db: AsyncSession, currency: str = "INR", receipt: str = "") -> dict:
    """Create a new order in Razorpay."""
    client = await _get_client(db)
    data = {
        "amount": int(amount * 100), # Razorpay expects paise
        "currency": currency,
        "receipt": receipt,
    }
    try:
        order = client.order.create(data=data)
        return order
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to create order: {str(e)}")

async def verify_payment(order_id: str, payment_id: str, signature: str, db: AsyncSession) -> bool:
    """Verify payment signature."""
    client = await _get_client(db)
    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        })
        return True
    except Exception:
        return False

async def process_webhook(body: str, signature: str, db: AsyncSession) -> bool:
    """Verify webhook signature."""
    # Webhook secret is usually static, but we can check DB too
    result_wh = await db.execute(select(AppSetting).where(AppSetting.key == "razorpay_webhook_secret"))
    db_wh = result_wh.scalar_one_or_none()
    wh_secret = db_wh.value if db_wh and db_wh.value else settings.RAZORPAY_WEBHOOK_SECRET

    if not wh_secret:
        return False
        
    client = await _get_client(db)
    try:
        client.utility.verify_webhook_signature(
            body, signature, wh_secret
        )
        return True
    except Exception:
        return False
