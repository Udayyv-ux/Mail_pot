import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from backend.config import settings

async def run():
    engine = create_async_engine(settings.DATABASE_URL)
    campaign_cols = [
        ("google_sheet_id", "VARCHAR"),
        ("target_columns", "VARCHAR DEFAULT 'Name, Email, Inquiry'"),
        ("status_column", "VARCHAR DEFAULT 'Status'"),
        ("follow_up_days", "INTEGER DEFAULT 0"),
        ("follow_up_template_id", "VARCHAR"),
        ("is_active", "BOOLEAN DEFAULT TRUE"),
        ("created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()")
    ]
    for col, col_def in campaign_cols:
        try:
            async with engine.begin() as conn:
                print(f"Adding {col}...")
                await conn.execute(text(f"ALTER TABLE campaigns ADD COLUMN {col} {col_def}"))
                print(f"Added {col}!")
        except Exception as e:
            print(f"Failed to add {col}: {e}")
            
asyncio.run(run())
