import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from backend.config import settings
from backend.models.client import Client

async def run():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine)
    async with async_session() as db:
        result = await db.execute(select(Client).where(Client.user_id == 'eae6db28-4b8f-4cc5-ab8f-1c0886340e27'))
        client = result.scalar_one_or_none()
        if client:
            print("Found client:", client.id)
            print("Client campaigns:", client.campaigns)
        else:
            print("No client found")
            
asyncio.run(run())
