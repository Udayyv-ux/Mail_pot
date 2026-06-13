"""
Razorpay integration service.
"""
import razorpay
from fastapi import HTTPException
from backend.config import settings

def _get_client():
    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=500, detail="Razorpay credentials not configured")
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def create_order(amount: float, currency: str = "INR", receipt: str = "") -> dict:
    """Create a new order in Razorpay."""
    client = _get_client()
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

def verify_payment(order_id: str, payment_id: str, signature: str) -> bool:
    """Verify payment signature."""
    client = _get_client()
    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        })
        return True
    except Exception:
        return False

def process_webhook(body: str, signature: str) -> bool:
    """Verify webhook signature."""
    if not settings.RAZORPAY_WEBHOOK_SECRET:
        return False
        
    client = _get_client()
    try:
        client.utility.verify_webhook_signature(
            body, signature, settings.RAZORPAY_WEBHOOK_SECRET
        )
        return True
    except Exception:
        return False
