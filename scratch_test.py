import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
from backend.config import settings

async def main():
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = async_sessionmaker(engine)
    async with async_session() as db:
        result = await db.execute(text("SELECT id, email, role FROM users LIMIT 1"))
        user = result.fetchone()
        if user:
            print(f"USER: {user.email} (Role: {user.role}) ID: {user.id}")
            from backend.middleware.auth_middleware import create_access_token
            token = create_access_token({'sub': user.id, 'role': user.role})
            print(f"TOKEN: {token}")
        else:
            print("No users found")

asyncio.run(main())
