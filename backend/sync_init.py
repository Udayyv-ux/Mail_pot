import os
from dotenv import load_dotenv
load_dotenv()

db_url = os.environ.get("DATABASE_URL")
if "+asyncpg" in db_url:
    db_url = db_url.replace("+asyncpg", "")

from sqlalchemy import create_engine
from backend.models.user import Base
import backend.models.client
import backend.models.plan
import backend.models.template
import backend.models.campaign
import backend.models.payment
import backend.models.app_settings

print(f"Connecting to {db_url.split('@')[1]}...")
engine = create_engine(db_url)

print("Dropping tables...")
Base.metadata.drop_all(engine)

print("Creating tables...")
Base.metadata.create_all(engine)

print("Done sync init!")
