"""
Google Sheets integration service.
"""
import gspread
import json
import re

from backend.config import settings

_gspread_client = None

def get_gspread_client():
    global _gspread_client
    if _gspread_client is None:
        if not settings.GOOGLE_SERVICE_ACCOUNT_JSON:
            raise ValueError("Missing Google Service Account credentials")
        creds_dict = json.loads(settings.GOOGLE_SERVICE_ACCOUNT_JSON)
        _gspread_client = gspread.service_account_from_dict(creds_dict)
    return _gspread_client

async def get_sheet_data(sheet_url_or_id: str) -> tuple[str, list]:
    """Connect to Google Sheets and return the extracted ID and records."""
    if not sheet_url_or_id:
        raise ValueError("Missing sheet ID")
        
    # Extract ID if URL is provided
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', sheet_url_or_id)
    sheet_id = match.group(1) if match else sheet_url_or_id.strip()
    
    try:
        gc = get_gspread_client()
        sheet = gc.open_by_key(sheet_id).sheet1
        records = sheet.get_all_values()
        return sheet_id, records
    except Exception as e:
        raise ValueError(f"Google Sheets connection failed: {str(e)}")

async def update_sheet_cell(sheet_id: str, row: int, col: int, value: str):
    """Update a specific cell in the sheet."""
    try:
        gc = get_gspread_client()
        sheet = gc.open_by_key(sheet_id).sheet1
        sheet.update_cell(row, col, value)
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
        gc = get_gspread_client()
        sheet = gc.open_by_key(sheet_id).sheet1
        cells = []
        for u in updates:
            cells.append(gspread.Cell(u['row'], u['col'], u['value']))
        sheet.update_cells(cells)
    except Exception as e:
        print(f"Failed to batch update sheet cells: {e}")
