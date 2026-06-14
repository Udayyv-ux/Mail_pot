import asyncio
from sqlalchemy import text
from backend.database import engine

async def main():
    try:
        async with engine.begin() as conn:
            await conn.execute(text("ALTER TABLE clients ADD COLUMN features_json TEXT DEFAULT '{}'"))
            print("Successfully added features_json to clients table")
    except Exception as e:
        print(f"Migration error (might already exist): {e}")

asyncio.run(main())
