import asyncio
import json
from sqlalchemy import text
from backend.database import engine

async def run():
    async with engine.begin() as conn:
        res2 = await conn.execute(text('SELECT key, value FROM app_settings WHERE category IN (\'landing\', \'branding\')'))
        for row in res2.fetchall():
            try:
                if row[1]:
                    json.loads(row[1])
                    print(f"{row[0]}: VALID JSON")
            except Exception as e:
                print(f"{row[0]}: INVALID JSON -> {e}")

if __name__ == "__main__":
    asyncio.run(run())
