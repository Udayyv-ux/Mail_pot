from sqlalchemy import Column, String, DateTime
from backend.database import Base
from datetime import datetime, timezone

class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    date = Column(String, nullable=False) # Format: YYYY-MM-DD
    time_slot = Column(String, nullable=False) # Format: HH:MM AM/PM
    status = Column(String, default="confirmed") # pending, confirmed, canceled
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
