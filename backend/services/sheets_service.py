"""
Google Sheets integration service.
"""
import gspread
import json
import re
from sqlalchemy import select
from backend.database import SessionLocal
from backend.models.app_settings import AppSetting
from backend.config import settings

_gspread_client = None
_cached_creds_str = None

async def get_gspread_client():
    global _gspread_client, _cached_creds_str
    
    async with SessionLocal() as db:
        res = await db.execute(select(AppSetting).where(AppSetting.key == 'GCP_CREDENTIALS_JSON'))
        setting = res.scalar_one_or_none()
        
        if not setting or not setting.value:
            if hasattr(settings, 'GOOGLE_SERVICE_ACCOUNT_JSON') and settings.GOOGLE_SERVICE_ACCOUNT_JSON:
                creds_str = settings.GOOGLE_SERVICE_ACCOUNT_JSON
            else:
                raise ValueError("Missing Google Service Account credentials in Super Admin Settings or Environment Variables")
        else:
            creds_str = setting.value
        
        # Only re-initialize if the credentials changed
        if _gspread_client is None or creds_str != _cached_creds_str:
            try:
                creds_dict = json.loads(creds_str)
                _gspread_client = gspread.service_account_from_dict(creds_dict)
                _cached_creds_str = creds_str
            except Exception as e:
                raise ValueError(f"Invalid Google Service Account JSON: {str(e)}")
                
    return _gspread_client

async def get_sheet_data(sheet_url_or_id: str) -> tuple[str, list]:
    """Connect to Google Sheets and return the extracted ID and records."""
    if not sheet_url_or_id:
        raise ValueError("Missing sheet ID")
        
    # Extract ID if URL is provided
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', sheet_url_or_id)
    sheet_id = match.group(1) if match else sheet_url_or_id.strip()
    
    try:
        gc = await get_gspread_client()
        import asyncio
        def _get():
            sheet = gc.open_by_key(sheet_id).sheet1
            return sheet.get_all_values()
        records = await asyncio.to_thread(_get)
        return sheet_id, records
    except Exception as e:
        raise ValueError(f"Google Sheets connection failed: {str(e)}")

async def update_sheet_cell(sheet_id: str, row: int, col: int, value: str):
    """Update a specific cell in the sheet."""
    try:
        gc = await get_gspread_client()
        import asyncio
        def _update():
            sheet = gc.open_by_key(sheet_id).sheet1
            sheet.update_cell(row, col, value)
        await asyncio.to_thread(_update)
    except Exception as e:
        print(f"Failed to update sheet cell: {e}")

async def update_sheet_cells_batch(sheet_id: str, updates: list):
    """
    Updates multiple cells in a single API call.
    updates is a list of dicts: [{'row': int, 'col': int, 'value': str}]
    """
    if not updates:
        return
    try:
        gc = await get_gspread_client()
        import asyncio
        def _batch_update():
            sheet = gc.open_by_key(sheet_id).sheet1
            cells = []
            for u in updates:
                cells.append(gspread.Cell(u['row'], u['col'], u['value']))
            sheet.update_cells(cells)
        await asyncio.to_thread(_batch_update)
    except Exception as e:
        print(f"Failed to batch update sheet cells: {e}")
