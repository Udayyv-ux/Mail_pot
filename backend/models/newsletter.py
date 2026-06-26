from sqlalchemy import Column, String, Boolean, DateTime
from backend.database import Base
from datetime import datetime, timezone

class NewsletterSubscriber(Base):
    __tablename__ = "newsletter_subscribers"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    mobile = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
