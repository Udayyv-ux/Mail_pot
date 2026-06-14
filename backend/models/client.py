"""
Client model — tenant record linked to a user account.
Stores per-client configuration (SMTP, Groq key, Sheet ID, etc.).
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.database import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    company_name = Column(String, default="")
    plan_id = Column(String, ForeignKey("plans.id"), nullable=True)
    is_demo = Column(Boolean, default=False)
    status = Column(String, default="active")  # active, suspended, trial

    # Email configuration (encrypted values)
    smtp_email = Column(String, nullable=True)
    smtp_password_enc = Column(Text, nullable=True)
    smtp_host = Column(String, default="smtp.gmail.com")
    smtp_port = Column(Integer, default=587)

    # AI configuration
    groq_api_key_enc = Column(Text, nullable=True)

    # Google Sheets
    google_sheet_id = Column(String, nullable=True)
    credentials_json = Column(Text, nullable=True)  # service account JSON (encrypted)

    # Usage tracking
    daily_email_limit = Column(Integer, default=50)
    emails_sent_today = Column(Integer, default=0)
    last_reset_date = Column(String, nullable=True)

    # Trial
    trial_ends_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Feature Flags
    features_json = Column(Text, default="{}")

    # Relationships
    user = relationship("User", backref="client_profile", lazy="selectin")
    plan = relationship("Plan", backref="subscribers", lazy="selectin")
    templates = relationship("Template", back_populates="client", cascade="all, delete-orphan", lazy="selectin")
    email_logs = relationship("EmailLog", back_populates="client", cascade="all, delete-orphan", lazy="selectin")
    payments = relationship("Payment", back_populates="client", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self):
        return f"<Client {self.company_name} (user={self.user_id})>"
