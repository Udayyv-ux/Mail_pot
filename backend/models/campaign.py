"""
Campaign and EmailLog models — tracks bulk email sending with per-email audit trail.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.database import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, default="Untitled Campaign")
    sheet_id = Column(String, nullable=True)
    status = Column(String, default="idle")  # idle, running, paused, completed, failed
    total_leads = Column(Integer, default=0)
    emails_sent = Column(Integer, default=0)
    emails_failed = Column(Integer, default=0)
    batch_size = Column(Integer, default=10)
    delay_seconds = Column(Integer, default=3)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    client = relationship("Client", back_populates="campaigns")
    email_logs = relationship("EmailLog", back_populates="campaign", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self):
        return f"<Campaign {self.name} ({self.status})>"


class EmailLog(Base):
    __tablename__ = "email_logs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    campaign_id = Column(String, ForeignKey("campaigns.id", ondelete="CASCADE"), nullable=False)
    recipient_email = Column(String, nullable=False)
    recipient_name = Column(String, default="")
    template_used = Column(String, default="")
    category_assigned = Column(String, default="")
    status = Column(String, default="queued")  # queued, sent, failed, bounced
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    campaign = relationship("Campaign", back_populates="email_logs")

    def __repr__(self):
        return f"<EmailLog {self.recipient_email} ({self.status})>"
