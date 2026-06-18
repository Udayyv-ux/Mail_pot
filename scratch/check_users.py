import asyncio
from sqlalchemy import select
from backend.database import SessionLocal
from backend.models.user import User

async def check_users():
    async with SessionLocal() as db:
        result = await db.execute(select(User))
        users = result.scalars().all()
        for u in users:
            print(f"User: {u.email}, Role: {u.role}, Active: {u.is_active}")

if __name__ == "__main__":
    asyncio.run(check_users())
