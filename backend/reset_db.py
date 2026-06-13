"""
Script to wipe all existing tables and re-seed the database.
WARNING: This destroys all data!
"""
import asyncio
from backend.database import engine, Base
from backend.seed_data import seed

async def reset_db():
    print("Dropping all existing tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    print("All tables dropped.")
    
    print("Re-creating tables and seeding data...")
    # seed() automatically calls init_db() which runs create_all
    await seed()

if __name__ == "__main__":
    asyncio.run(reset_db())
