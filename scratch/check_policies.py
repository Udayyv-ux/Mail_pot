import asyncio
from sqlalchemy import select
from backend.database import SessionLocal
from backend.models.app_settings import Policy

async def run():
    async with SessionLocal() as db:
        res = await db.execute(select(Policy))
        policies = res.scalars().all()
        for p in policies:
            print(f"{p.slug} - {p.title}")

asyncio.run(run())
