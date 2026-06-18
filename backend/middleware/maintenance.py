from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import select
from backend.database import SessionLocal
from backend.models.app_settings import AppSetting
import time

# Cache the maintenance mode status to avoid DB hits on every single request
_maintenance_cache = {"is_active": False, "last_checked": 0}

async def maintenance_middleware(request: Request, call_next):
    # Only protect client routes and client api
    path = request.url.path
    if path.startswith("/client") or path.startswith("/api/client"):
        
        now = time.time()
        if now - _maintenance_cache["last_checked"] > 10:  # refresh every 10 seconds
            try:
                async with SessionLocal() as db:
                    res = await db.execute(select(AppSetting).where(AppSetting.key == "MAINTENANCE_MODE"))
                    setting = res.scalar_one_or_none()
                    _maintenance_cache["is_active"] = (setting and setting.value.lower() == "true")
                    _maintenance_cache["last_checked"] = now
            except Exception:
                pass
        
        if _maintenance_cache["is_active"]:
            if path.startswith("/api/"):
                return JSONResponse(
                    status_code=503,
                    content={"detail": "System is currently undergoing maintenance. Please try again shortly."}
                )
            else:
                return RedirectResponse(url="/maintenance.html")
                
    response = await call_next(request)
    return response
