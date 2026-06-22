"""
App-level settings — Policies, Dynamic Config, Demo Requests.
All editable from Super Admin without touching code.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Text
from backend.database import Base


class Policy(Base):
    __tablename__ = "policies"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String, nullable=False)
    slug = Column(String, unique=True, nullable=False)  # e.g. "terms", "privacy", "refund"
    icon = Column(String, default="📜")
    description = Column(String, default="")
    content_html = Column(Text, default="")
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Policy {self.slug}>"


class AppSetting(Base):
    """Key-value store for dynamic application configuration.
    Categories: branding, email, limits, landing, razorpay, general
    """
    __tablename__ = "app_settings"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    key = Column(String, unique=True, nullable=False, index=True)
    value = Column(Text, default="")
    category = Column(String, default="general")
    description = Column(String, default="")

    def __repr__(self):
        return f"<AppSetting {self.key}={self.value[:30]}>"


class DemoRequest(Base):
    __tablename__ = "demo_requests"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    company = Column(String, default="")
    phone = Column(String, default="")
    message = Column(Text, default="")
    inquiry_type = Column(String, default="Demo")
    status = Column(String, default="pending")  # pending, approved, rejected
    user_id = Column(String, ForeignKey("users.id"), nullable=True)  # linked after approval
    scheduled_time = Column(String, nullable=True)  # e.g., 2026-06-25T14:30
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<DemoRequest {self.email} ({self.status})>"

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    message = Column(Text, nullable=False)
    type = Column(String, default="info") # info, warning, success
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Notification {self.type}>"
