import asyncio
from backend.config import settings
from backend.services.sheets_service import get_sheet_data

async def main():
    try:
        sheet_url = "10B6Z4Bv4M2a2n7bB3o0U-L7Hl-1tZ9H3v4M2a2n7bB3o0U-L" # fake id
        print(await get_sheet_data(sheet_url))
    except Exception as e:
        print("ERROR:", str(e))

asyncio.run(main())
