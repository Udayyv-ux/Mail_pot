import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from backend.config import settings
from backend.models.app_settings import FAQ, Policy

async def run():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine)
    async with async_session() as db:
        faqs = (await db.execute(select(FAQ))).scalars().all()
        policies = (await db.execute(select(Policy))).scalars().all()
        print("FAQs:", len(faqs))
        print("Policies:", len(policies))
            
asyncio.run(run())
