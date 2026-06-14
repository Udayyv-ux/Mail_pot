"""
EmailLog model — tracks bulk email sending with per-email audit trail.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.database import Base

class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    recipient_email = Column(String, nullable=False)
    recipient_name = Column(String, default="")
    template_used = Column(String, default="")
    category_assigned = Column(String, default="")
    status = Column(String, default="queued")  # queued, sent, failed, bounced
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    client = relationship("Client", back_populates="email_logs")

    def __repr__(self):
        return f"<EmailLog {self.recipient_email} ({self.status})>"
