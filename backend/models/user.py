"""
User model — stores all authenticated users (clients, admins, demo users).
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Enum as SAEnum
from backend.database import Base
import enum


class UserRole(str, enum.Enum):
    CLIENT = "client"
    ADMIN = "admin"
    SUB_ADMIN = "sub_admin"
    DEMO = "demo"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False, default="")
    hashed_password = Column(String, nullable=True) # Used for sub-admins
    google_id = Column(String, unique=True, nullable=True)
    google_access_token = Column(String, nullable=True)
    google_refresh_token = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    role = Column(SAEnum(UserRole), default=UserRole.CLIENT, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<User {self.email} ({self.role.value})>"
