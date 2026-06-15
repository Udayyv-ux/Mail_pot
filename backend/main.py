"""
FastAPI application entry point.
Registers all routers, serves frontend static files, and manages lifecycle events.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from backend.config import settings
from backend.database import init_db

# ── Lifecycle ────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    print(f"Starting {settings.APP_NAME}...")
    await init_db()  # Tables already exist, avoid duplicate table error
    
    from backend.database import engine, Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    # Add new columns manually to existing tables (sqlite & postgres)
    for col, col_def in [("target_columns", "VARCHAR DEFAULT 'Name, Email, Inquiry'"), ("status_column", "VARCHAR DEFAULT 'Status'")]:
        try:
            async with engine.begin() as conn:
                from sqlalchemy import text
                await conn.execute(text(f"ALTER TABLE clients ADD COLUMN {col} {col_def}"))
        except Exception: pass
    
    try:
        async with engine.begin() as conn:
            from sqlalchemy import text
            await conn.execute(text(f"ALTER TABLE templates ADD COLUMN banner_url VARCHAR"))
    except Exception: pass
    
    for col, col_def in [("google_access_token", "VARCHAR"), ("google_refresh_token", "VARCHAR")]:
        try:
            async with engine.begin() as conn:
                from sqlalchemy import text
                await conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {col_def}"))
        except Exception: pass
        
    try:
        async with engine.begin() as conn:
            from sqlalchemy import text
            await conn.execute(text(f"ALTER TABLE email_logs ADD COLUMN client_id VARCHAR"))
    except Exception: pass

    for col, col_def in [("recipient_name", "VARCHAR"), ("template_used", "VARCHAR"), ("category_assigned", "VARCHAR"), ("error_message", "TEXT")]:
        try:
            async with engine.begin() as conn:
                from sqlalchemy import text
                await conn.execute(text(f"ALTER TABLE email_logs ADD COLUMN {col} {col_def}"))
        except Exception: pass
        
    try:
        async with engine.begin() as conn:
            from sqlalchemy import text
            await conn.execute(text("ALTER TABLE email_logs ALTER COLUMN campaign_id DROP NOT NULL"))
    except Exception: pass
        
    print("Database ready")

    # Start the 24/7 background engine
    from backend.services.email_engine import run_247_engine
    import asyncio
    global engine_task
    engine_task = asyncio.create_task(run_247_engine())

    # Setup OAuth
    try:
        from backend.services.auth_service import setup_oauth
        setup_oauth(app)
        print("Google OAuth configured")
    except Exception as e:
        print(f"OAuth not configured: {e}")

    yield

    # Shutdown engine tasks if any
    if engine_task:
        engine_task.cancel()
    print(f"{settings.APP_NAME} shut down.")


# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise Email Automation SaaS Platform",
    version="2.0.0",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────

from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=["*"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.JWT_SECRET,
    same_site="lax",
    https_only=False
)

# ── Register API Routers ─────────────────────────────────────────────────────

from backend.routers.auth import router as auth_router
from backend.routers.admin import router as admin_router
from backend.routers.client_api import router as client_router
from backend.routers.templates_api import router as templates_router
from backend.routers.payments import router as payments_router
from backend.routers.public import router as public_router

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(client_router)
app.include_router(templates_router)
app.include_router(payments_router)
app.include_router(public_router)

# ── Static Files ──────────────────────────────────────────────────────────────

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

# Serve CSS, JS, assets as static files
app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")
if os.path.exists(os.path.join(FRONTEND_DIR, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")

UPLOADS_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")


# ── Frontend Page Routes ─────────────────────────────────────────────────────



@app.get("/")
async def landing_page():
    """Serve the space-themed landing page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"), headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/policy.html")
async def policy_page():
    """Serve the policy viewer page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "policy.html"), headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


@app.get("/client")
async def client_portal_redirect():
    return RedirectResponse("/client/")


@app.get("/client/")
async def client_portal():
    """Serve the client portal SPA."""
    return FileResponse(os.path.join(FRONTEND_DIR, "client", "index.html"), headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


@app.get("/admin")
async def admin_portal_redirect():
    return RedirectResponse("/admin/")


@app.get("/admin/")
async def admin_portal():
    """Serve the super admin portal SPA."""
    return FileResponse(os.path.join(FRONTEND_DIR, "admin", "index.html"), headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


# ── Health Check ──────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "app": settings.APP_NAME, "version": "2.0.0"}