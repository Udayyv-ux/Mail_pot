import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from backend.config import settings

async def run():
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE plans ADD COLUMN price_half_yearly FLOAT DEFAULT 0.0"))
            print("Successfully added price_half_yearly column.")
        except Exception as e:
            print("Failed (maybe already exists?):", e)
    await engine.dispose()

asyncio.run(run())
