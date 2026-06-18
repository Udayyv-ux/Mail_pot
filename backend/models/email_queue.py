from sqlalchemy import Column, String, ForeignKey, DateTime, Boolean, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

from backend.database import Base

class EmailQueue(Base):
    __tablename__ = "email_queue"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, ForeignKey("clients.id", ondelete="CASCADE"))
    campaign_id = Column(String, ForeignKey("campaigns.id", ondelete="CASCADE"))
    template_id = Column(String, ForeignKey("templates.id", ondelete="CASCADE"))
    
    recipient_email = Column(String, nullable=False)
    recipient_name = Column(String, nullable=True)
    
    # "pending", "approved", "rejected", "sent"
    status = Column(String, default="pending")
    
    # To store rendered email content or specific context if needed
    context_data = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    client = relationship("Client")
    campaign = relationship("Campaign")
    template = relationship("Template")
