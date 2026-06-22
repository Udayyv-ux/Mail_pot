import asyncio
from backend.database import SessionLocal
from backend.models.campaign import Campaign
from backend.services.sheets_service import get_sheet_data

async def run():
    async with SessionLocal() as db:
        from sqlalchemy import select
        res = await db.execute(select(Campaign).where(Campaign.name == "xc"))
        campaign = res.scalars().first()
        if not campaign:
            print("Campaign xc not found")
            return
            
        print(f"Target Cols: {campaign.target_columns}")
        print(f"Status Col: {campaign.status_column}")
        
        try:
            sheet_id, rows = await get_sheet_data(campaign.google_sheet_id)
            if rows:
                print(f"Headers: {rows[0]}")
                print(f"First row: {rows[1] if len(rows) > 1 else 'No data'}")
        except Exception as e:
            print(f"Sheet error: {e}")

asyncio.run(run())
