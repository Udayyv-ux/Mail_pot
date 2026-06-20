"""
Payment model — Razorpay transaction records.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from backend.database import Base


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    plan_id = Column(String, ForeignKey("plans.id"), nullable=True)
    amount = Column(Float, nullable=False)
    currency = Column(String, default="INR")
    billing_cycle = Column(String, default="monthly")
    razorpay_order_id = Column(String, nullable=True, index=True)
    razorpay_payment_id = Column(String, nullable=True, index=True)
    razorpay_signature = Column(String, nullable=True)
    status = Column(String, default="created")  # created, paid, failed, refunded
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    client = relationship("Client", back_populates="payments")
    plan = relationship("Plan")

    def __repr__(self):
        return f"<Payment ₹{self.amount} ({self.status})>"
