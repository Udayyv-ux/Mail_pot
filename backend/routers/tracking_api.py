from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.models.email_log import EmailLog
from datetime import datetime, timezone
import base64

router = APIRouter(prefix="/api/track", tags=["Tracking"])

# A 1x1 transparent GIF (Base64 encoded)
TRANSPARENT_PIXEL_B64 = "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7"

@router.get("/open/{log_id}")
async def track_email_open(log_id: str, db: AsyncSession = Depends(get_db)):
    """
    Returns a 1x1 invisible pixel and marks the email as opened in the database.
    """
    try:
        log = await db.get(EmailLog, log_id)
        if log and not log.opened:
            log.opened = True
            log.opened_at = datetime.now(timezone.utc)
            await db.commit()
    except Exception as e:
        print(f"Tracking error: {e}")
        
    pixel_data = base64.b64decode(TRANSPARENT_PIXEL_B64)
    return Response(content=pixel_data, media_type="image/gif", headers={
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
        "Pragma": "no-cache",
        "Expires": "0"
    })
