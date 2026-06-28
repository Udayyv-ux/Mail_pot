"""
Campaign model — linking a specific Google Sheet and follow-up rules to a Client.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.database import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    
    # Google Sheets Configuration
    google_sheet_id = Column(String, nullable=False)
    target_columns = Column(String, default="Name, Email, Inquiry")
    status_column = Column(String, default="Status")
    inquiry_column = Column(String, default="Inquiry")
    default_template_id = Column(String, ForeignKey("templates.id", ondelete="SET NULL"), nullable=True)
    
    # WhatsApp Configuration
    use_whatsapp = Column(Boolean, default=False)
    default_whatsapp_template_name = Column(String, nullable=True)
    follow_up_whatsapp_template_name = Column(String, nullable=True)
    
    # Follow-up Logic
    follow_up_days = Column(Integer, default=0) # 0 means no follow up
    follow_up_template_id = Column(String, ForeignKey("templates.id", ondelete="SET NULL"), nullable=True)
    follow_up_condition = Column(String, default="always")
    
    # Smart Scheduling & Throttling
    max_emails_per_hour = Column(Integer, default=50) # default safe limit
    send_hours_start = Column(Integer, default=9)  # 9 AM
    send_hours_end = Column(Integer, default=17)   # 5 PM
    
    # Review Before Send
    review_mode = Column(Boolean, default=False)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_run_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)

    # Relationships
    client = relationship("Client", back_populates="campaigns", lazy="selectin")
    follow_up_template = relationship("Template", foreign_keys="[Campaign.follow_up_template_id]", lazy="selectin")
    default_template = relationship("Template", foreign_keys="[Campaign.default_template_id]", lazy="selectin")
    email_logs = relationship("EmailLog", back_populates="campaign", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self):
        return f"<Campaign {self.name} (client={self.client_id})>"
