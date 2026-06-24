import asyncio
from sqlalchemy import select, update
from backend.database import engine, SessionLocal
from backend.models.plan import Plan

async def main():
    async with SessionLocal() as db:
        # Check current plans
        result = await db.execute(select(Plan))
        plans = result.scalars().all()
        for p in plans:
            print(f'Plan: {p.name}, AI: {getattr(p, "has_ai_templates", False)}')
            
            # Enable AI for Growth and Ultra/Ultimate
            if "Growth" in p.name or "Ultra" in p.name or "Ultimate" in p.name:
                p.has_ai_templates = True
                print(f' -> Enabled AI for {p.name}')
                
        await db.commit()
        print('Database plans updated.')

asyncio.run(main())
