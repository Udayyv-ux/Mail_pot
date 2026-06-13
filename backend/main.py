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
    # await init_db()  # Tables already exist, avoid duplicate table error
    print("Database ready")

    # Start email queue workers
    try:
        from backend.services.queue_manager import queue_manager
        await queue_manager.start_workers(num_workers=5)
        print("Email queue workers started")
    except Exception as e:
        print(f"Queue manager not started: {e}")

    # Setup OAuth
    try:
        from backend.services.auth_service import setup_oauth
        setup_oauth(app)
        print("Google OAuth configured")
    except Exception as e:
        print(f"OAuth not configured: {e}")

    yield

    # Shutdown
    try:
        from backend.services.queue_manager import queue_manager
        await queue_manager.stop()
        print("Email queue workers stopped")
    except Exception:
        pass
    print(f"{settings.APP_NAME} shut down.")


# ── App ──────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.APP_NAME,
    description="Enterprise Email Automation SaaS Platform",
    version="2.0.0",
    lifespan=lifespan,
)

# ── Middleware ────────────────────────────────────────────────────────────────

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
)

# ── Register API Routers ─────────────────────────────────────────────────────

from backend.routers.auth import router as auth_router
from backend.routers.admin import router as admin_router
from backend.routers.client_api import router as client_router
from backend.routers.templates_api import router as templates_router
from backend.routers.campaigns import router as campaigns_router
from backend.routers.payments import router as payments_router
from backend.routers.public import router as public_router

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(client_router)
app.include_router(templates_router)
app.include_router(campaigns_router)
app.include_router(payments_router)
app.include_router(public_router)

# ── Static Files ──────────────────────────────────────────────────────────────

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

# Serve CSS, JS, assets as static files
app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")
if os.path.exists(os.path.join(FRONTEND_DIR, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")


# ── Frontend Page Routes ─────────────────────────────────────────────────────

@app.get("/")
async def landing_page():
    """Serve the space-themed landing page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


@app.get("/client")
async def client_portal_redirect():
    return RedirectResponse("/client/")


@app.get("/client/")
async def client_portal():
    """Serve the client portal SPA."""
    return FileResponse(os.path.join(FRONTEND_DIR, "client", "index.html"))


@app.get("/admin")
async def admin_portal_redirect():
    return RedirectResponse("/admin/")


@app.get("/admin/")
async def admin_portal():
    """Serve the super admin portal SPA."""
    return FileResponse(os.path.join(FRONTEND_DIR, "admin", "index.html"))


# ── Health Check ──────────────────────────────────────────────────────────────

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "app": settings.APP_NAME, "version": "2.0.0"}