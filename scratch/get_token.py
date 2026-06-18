import asyncio
from backend.database import SessionLocal
from backend.models.user import User
from backend.middleware.auth_middleware import create_access_token
from sqlalchemy import select

async def get_test_token():
    async with SessionLocal() as db:
        result = await db.execute(select(User).where(User.email == "ambatman444@gmail.com"))
        user = result.scalar_one_or_none()
        if not user:
            print("User not found")
            return
        
        token = create_access_token({"sub": user.id, "role": user.role.value})
        print(f"TEST_TOKEN={token}")

if __name__ == "__main__":
    asyncio.run(get_test_token())
