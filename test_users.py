import asyncio
from sqlalchemy import select
from backend.database import SessionLocal
from backend.models.user import User

async def main():
    async with SessionLocal() as db:
        res = await db.execute(select(User))
        users = res.scalars().all()
        for u in users:
            print(f"User: {u.email} | Role: {u.role}")

asyncio.run(main())
