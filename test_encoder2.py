import asyncio
import io
import sys
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select
from backend.config import settings
from backend.models.campaign import Campaign
from fastapi.encoders import jsonable_encoder

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8')

async def run():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine)
    async with async_session() as db:
        result = await db.execute(select(Campaign).limit(1))
        campaigns = result.scalars().all()
        try:
            enc = jsonable_encoder(campaigns)
            print("Encoding length:", len(str(enc)))
            print("First item keys:", list(enc[0].keys()) if enc else "empty")
        except Exception as e:
            print("ERROR ENCODING:", str(e))

asyncio.run(run())
