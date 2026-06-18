import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from backend.config import settings
from backend.models.campaign import Campaign

async def run():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine)
    async with async_session() as db:
        # get campaigns for user
        result = await db.execute(select(Campaign))
        campaigns = result.scalars().all()
        print(campaigns)

asyncio.run(run())
