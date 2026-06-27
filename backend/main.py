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
from backend.database import init_db, get_db
from fastapi import Depends

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
    try:
        from sqlalchemy import text
        async with engine.begin() as conn:
            await conn.execute(text("UPDATE plans SET is_featured = true WHERE name = 'Growth'"))
    except Exception as e:
        print(f"Plan update failed: {e}")
        
    migrations = [
        ("campaigns", "default_template_id", "VARCHAR"),
        ("campaigns", "use_whatsapp", "BOOLEAN DEFAULT FALSE"),
        ("campaigns", "inquiry_column", "VARCHAR DEFAULT 'Inquiry'"),
        ("clients", "whatsapp_access_token", "TEXT"),
        ("clients", "whatsapp_phone_number_id", "VARCHAR"),
        ("clients", "whatsapp_business_account_id", "VARCHAR"),
        ("templates", "whatsapp_template_name", "VARCHAR"),
        ("clients", "target_columns", "VARCHAR DEFAULT 'Name, Email, Inquiry'"),
        ("clients", "status_column", "VARCHAR DEFAULT 'Status'"),
        ("templates", "banner_url", "VARCHAR"),
        ("users", "google_access_token", "VARCHAR"),
        ("users", "google_refresh_token", "VARCHAR"),
        ("email_logs", "client_id", "VARCHAR"),
        ("email_logs", "campaign_id", "VARCHAR"),
        ("email_logs", "recipient_name", "VARCHAR"),
        ("email_logs", "template_used", "VARCHAR"),
        ("email_logs", "category_assigned", "VARCHAR"),
        ("email_logs", "error_message", "TEXT"),
        ("email_logs", "is_follow_up", "BOOLEAN DEFAULT FALSE"),
        ("email_logs", "whatsapp_sent", "BOOLEAN DEFAULT FALSE"),
        ("email_logs", "thread_id", "VARCHAR"),
        ("email_logs", "opened", "BOOLEAN DEFAULT FALSE"),
        ("email_logs", "opened_at", "TIMESTAMP WITH TIME ZONE"),
        ("email_logs", "reply_status", "VARCHAR DEFAULT 'no_reply'"),
        ("email_logs", "reply_text", "TEXT"),
        ("campaigns", "max_emails_per_hour", "INTEGER DEFAULT 50"),
        ("campaigns", "send_hours_start", "INTEGER DEFAULT 9"),
        ("campaigns", "send_hours_end", "INTEGER DEFAULT 17"),
        ("campaigns", "review_mode", "BOOLEAN DEFAULT FALSE"),
        ("campaigns", "google_sheet_id", "VARCHAR"),
        ("campaigns", "target_columns", "VARCHAR DEFAULT 'Name, Email, Inquiry'"),
        ("campaigns", "status_column", "VARCHAR DEFAULT 'Status'"),
        ("campaigns", "follow_up_days", "INTEGER DEFAULT 0"),
        ("campaigns", "follow_up_template_id", "VARCHAR"),
        ("campaigns", "default_whatsapp_template_name", "VARCHAR"),
        ("campaigns", "follow_up_whatsapp_template_name", "VARCHAR"),
        ("campaigns", "follow_up_condition", "VARCHAR DEFAULT 'always'"),
        ("campaigns", "is_active", "BOOLEAN DEFAULT TRUE"),
        ("campaigns", "created_at", "TIMESTAMP WITH TIME ZONE DEFAULT NOW()"),
        ("policies", "icon", "VARCHAR DEFAULT '📜'"),
        ("policies", "description", "VARCHAR DEFAULT ''"),
        ("demo_requests", "inquiry_type", "VARCHAR DEFAULT 'Demo'"),
    ]

    from sqlalchemy import text
    try:
        async with engine.connect() as conn:
            for table, col, col_def in migrations:
                try:
                    await conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}"))
                    await conn.commit()
                except Exception:
                    await conn.rollback()
                    pass

            try:
                await conn.execute(text("ALTER TABLE email_logs ALTER COLUMN campaign_id DROP NOT NULL"))
                await conn.commit()
            except Exception:
                await conn.rollback()
                pass

            try:
                await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS promo_codes (
                    id VARCHAR PRIMARY KEY,
                    code VARCHAR UNIQUE NOT NULL,
                    discount_pct INTEGER NOT NULL,
                    max_uses INTEGER DEFAULT 100,
                    uses INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
                """))
                await conn.commit()
            except Exception:
                await conn.rollback()
                pass
    except Exception as e:
        print(f"Schema migration error: {e}")

    # Seed Policies
    try:
        async with engine.begin() as conn:
            from sqlalchemy import text
            # Check if policies already exist
            res = await conn.execute(text("SELECT COUNT(*) FROM policies"))
            count = res.scalar()
            if count == 0:
                print("Seeding initial policies...")
                from backend.models.app_settings import Policy
                import uuid
                default_policies = [
                    ("Terms & Conditions", "terms", "Rules governing the use of Sheetx.io services and website.", "📜"),
                    ("Privacy Policy", "privacy-policy", "How we collect, use, and protect personal information.", "🔒"),
                    ("Consent Policy", "consent-policy", "How consent is obtained, recorded, and respected.", "✅"),
                    ("Safeguarding Policy", "safeguarding-policy", "Protecting users and ensuring safe platform usage.", "🛡️"),
                    ("Modern Slavery Statement", "modern-slavery-statement", "Our commitment to ethical operations and anti-slavery.", "🤝"),
                    ("Carbon Reduction Plan", "carbon-reduction-plan", "Our steps to minimize environmental impact.", "🌱")
                ]
                for title, slug, desc, icon in default_policies:
                    await conn.execute(
                        text("INSERT INTO policies (id, title, slug, description, icon, content_html, is_active) VALUES (:id, :title, :slug, :desc, :icon, :content, true)"),
                        {"id": str(uuid.uuid4()), "title": title, "slug": slug, "desc": desc, "icon": icon, "content": f"<h2>{title}</h2><p>This is a placeholder for the {title}. Please update it from the Super Admin dashboard.</p>"}
                    )
    except Exception as e: 
        print(f"Policy seed failed: {e}")

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

from backend.middleware.maintenance import maintenance_middleware
app.middleware("http")(maintenance_middleware)

# ── Register API Routers ─────────────────────────────────────────────────────

from backend.routers.auth import router as auth_router
from backend.routers.admin import router as admin_router
from backend.routers.client_api import router as client_router
from backend.routers.templates_api import router as templates_router
from backend.routers.payments import router as payments_router
from backend.routers.public import router as public_router
from backend.routers.tracking_api import router as tracking_router

app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(client_router)
app.include_router(templates_router)
app.include_router(payments_router)
app.include_router(public_router)
app.include_router(tracking_router)

# ── Static Files ──────────────────────────────────────────────────────────────

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend")

# Serve CSS, JS, assets as static files
app.mount("/css", StaticFiles(directory=os.path.join(FRONTEND_DIR, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(FRONTEND_DIR, "js")), name="js")
if os.path.exists(os.path.join(FRONTEND_DIR, "assets")):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIR, "assets")), name="assets")

@app.get("/api/images/{image_id}")
async def get_uploaded_image(image_id: str, db = Depends(get_db)):
    from sqlalchemy import select
    from backend.models.image import UploadedImage
    result = await db.execute(select(UploadedImage).where(UploadedImage.id == image_id))
    img = result.scalar_one_or_none()
    if not img or not img.data_uri.startswith("data:image"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Image not found")
        
    header, b64 = img.data_uri.split(",", 1)
    mime = header.split(":")[1].split(";")[0]
    import base64
    from fastapi.responses import Response
    img_data = base64.b64decode(b64)
    return Response(content=img_data, media_type=mime, headers={"Cache-Control": "public, max-age=31536000"})


# ── Frontend Page Routes ─────────────────────────────────────────────────────

@app.get("/api/logo")
async def get_site_logo(db = Depends(get_db)):
    """Serve the active site logo, or a transparent fallback."""
    from fastapi.responses import Response
    import base64
    from sqlalchemy import select
    from backend.models.app_settings import AppSetting

    result = await db.execute(select(AppSetting).where(AppSetting.key == "SITE_LOGO"))
    setting = result.scalar_one_or_none()
    
    if setting and setting.value:
        try:
            if setting.value.startswith("data:"):
                header, b64 = setting.value.split(",", 1)
                mime = header.split(":")[1].split(";")[0]
                if "octet-stream" in mime or not mime.startswith("image/"):
                    mime = "image/png"
                img_data = base64.b64decode(b64)
                return Response(content=img_data, media_type=mime, headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                })
        except Exception:
            pass
            
    # Fallback: Transparent 1x1 GIF
    fallback_gif = base64.b64decode("R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")
    return Response(content=fallback_gif, media_type="image/gif", headers={
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0"
    })


@app.get("/")
async def landing_page():
    """Serve the space-themed landing page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"), headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/legal.html")
async def legal_page():
    """Serve the dedicated legal policies page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "legal.html"), headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/policy.html")
async def policy_page():
    """Serve the policy viewer page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "policy.html"), headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/maintenance.html")
async def maintenance_page():
    """Serve the maintenance screen."""
    return FileResponse(os.path.join(FRONTEND_DIR, "maintenance.html"), headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/docs.html")
async def docs_page():
    """Serve the documentation page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "docs.html"), headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/help.html")
async def help_page():
    """Serve the help centre page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "help.html"), headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/status.html")
async def status_page():
    """Serve the system status page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "status.html"), headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/feedback.html")
async def feedback_page():
    """Serve the feedback page."""
    return FileResponse(os.path.join(FRONTEND_DIR, "feedback.html"), headers={"Cache-Control": "no-cache, no-store, must-revalidate"})

@app.get("/admin-login.html")
async def admin_login_page():
    """Serve the admin login page for sub-admins."""
    return FileResponse(os.path.join(FRONTEND_DIR, "admin-login.html"), headers={"Cache-Control": "no-cache, no-store, must-revalidate"})


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