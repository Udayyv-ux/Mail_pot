from sqlalchemy import Column, String, Integer, Boolean, DateTime
from datetime import datetime, timezone
import uuid

from backend.database import Base

class PromoCode(Base):
    __tablename__ = "promo_codes"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String, unique=True, index=True, nullable=False)
    discount_pct = Column(Integer, nullable=False) # e.g. 15 for 15% off
    max_uses = Column(Integer, default=100)
    uses = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
