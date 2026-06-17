import asyncio
from sqlalchemy import text
from backend.database import engine

async def run():
    async with engine.begin() as conn:
        try:
            res = await conn.execute(text('SELECT slug, title, is_active FROM policies'))
            print("Policies:", res.fetchall())
            res2 = await conn.execute(text('SELECT key, value FROM app_settings WHERE category IN (\'landing\', \'branding\')'))
            print("Settings:")
            for row in res2.fetchall():
                print(f"{row[0]}: {row[1][:50]}...")
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    asyncio.run(run())
