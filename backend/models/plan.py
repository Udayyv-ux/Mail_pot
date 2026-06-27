"""
Plan model — subscription tiers with pricing and limits.
Editable from Super Admin.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, Text
from backend.database import Base


class Plan(Base):
    __tablename__ = "plans"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, unique=True)
    description = Column(Text, default="")
    price_monthly = Column(Float, default=0.0)
    price_half_yearly = Column(Float, default=0.0)
    price_yearly = Column(Float, default=0.0)
    email_limit_daily = Column(Integer, default=50)
    template_limit = Column(Integer, default=5)
    campaign_limit = Column(Integer, default=3)
    features_json = Column(Text, default="[]")  # JSON array of feature strings
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)  # Highlighted on landing page
    has_ai_templates = Column(Boolean, default=False)  # Allows using AI generation in templates
    ai_limit = Column(Integer, default=-1) # -1 means unlimited, 0 means none
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Plan {self.name} ₹{self.price_monthly}/mo>"
