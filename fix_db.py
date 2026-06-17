import asyncio
from sqlalchemy import text
from backend.database import engine

async def run():
    async with engine.begin() as conn:
        try:
            await conn.execute(text('ALTER TABLE campaigns ADD COLUMN google_sheet_id VARCHAR;'))
            print("Added google_sheet_id")
        except Exception as e:
            print("Error google_sheet_id:", e)
        try:
            await conn.execute(text('ALTER TABLE campaigns ADD COLUMN target_columns VARCHAR DEFAULT \'Name, Email, Inquiry\';'))
            print("Added target_columns")
        except Exception as e:
            print("Error target_columns:", e)
        try:
            await conn.execute(text('ALTER TABLE campaigns ADD COLUMN status_column VARCHAR DEFAULT \'Status\';'))
            print("Added status_column")
        except Exception as e:
            print("Error status_column:", e)

if __name__ == "__main__":
    asyncio.run(run())
