"""
Google Sheets integration service.
"""
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
import re

SCOPE = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

from backend.config import settings

async def get_sheet_data(sheet_url_or_id: str) -> tuple[str, list]:
    """Connect to Google Sheets and return the extracted ID and records."""
    if not sheet_url_or_id or not settings.GOOGLE_SERVICE_ACCOUNT_JSON:
        raise ValueError("Missing sheet ID or central credentials")
        
    # Extract ID if URL is provided
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', sheet_url_or_id)
    sheet_id = match.group(1) if match else sheet_url_or_id.strip()
    
    try:
        creds_dict = json.loads(settings.GOOGLE_SERVICE_ACCOUNT_JSON)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(sheet_id).sheet1
        records = sheet.get_all_values()
        return sheet_id, records
    except Exception as e:
        raise ValueError(f"Google Sheets connection failed: {str(e)}")

async def update_sheet_cell(sheet_id: str, row: int, col: int, value: str):
    """Update a specific cell in the sheet."""
    try:
        creds_dict = json.loads(settings.GOOGLE_SERVICE_ACCOUNT_JSON)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, SCOPE)
        gc = gspread.authorize(creds)
        sheet = gc.open_by_key(sheet_id).sheet1
        sheet.update_cell(row, col, value)
    except Exception as e:
        print(f"Failed to update sheet cell: {e}")
