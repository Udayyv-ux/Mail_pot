import asyncio
import io
import sys
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from backend.config import settings
from backend.models.campaign import Campaign
from backend.models.client import Client
import uuid

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8')

async def run():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine)
    async with async_session() as db:
        result = await db.execute(select(Client).limit(1))
        client = result.scalar_one_or_none()
        
        # Insert a new campaign
        new_c = Campaign(
            id=str(uuid.uuid4()),
            client_id=client.id,
            name="Test Campaign 123",
            google_sheet_id="1x2y3z",
        )
        db.add(new_c)
        await db.commit()
        
        print("Inserted campaign")
        
        # Get campaigns
        result = await db.execute(select(Campaign).where(Campaign.client_id == client.id).order_by(Campaign.created_at.desc()))
        campaigns = result.scalars().all()
        print("Found:", len(campaigns))

asyncio.run(run())
