from sqlalchemy import Column, String, ForeignKey
import uuid
from backend.database import Base

class UploadedImage(Base):
    __tablename__ = "uploaded_images"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = Column(String, ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    data_uri = Column(String, nullable=False)  # Stores data:image/png;base64,...
