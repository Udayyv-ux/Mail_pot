import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from backend.config import settings
from backend.models.app_settings import AppSetting

async def run():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine)
    async with async_session() as db:
        result = await db.execute(select(AppSetting))
        print("Success:", len(result.scalars().all()))
            
asyncio.run(run())
