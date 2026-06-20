"""
Authentication service handling Google OAuth flow and user management.
"""
from authlib.integrations.starlette_client import OAuth
from starlette.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException
import uuid

from backend.config import settings
from backend.models.user import User, UserRole
from backend.models.client import Client
from backend.models.app_settings import DemoRequest
from backend.middleware.auth_middleware import create_access_token, create_refresh_token

oauth = OAuth()

def setup_oauth(app):
    """Register Google OAuth client."""
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        print("⚠️ Google OAuth credentials not found in settings.")
        return

    oauth.register(
        name='google',
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={
            'scope': 'openid email profile https://www.googleapis.com/auth/gmail.send https://www.googleapis.com/auth/gmail.readonly',
            'access_type': 'offline',
            'prompt': 'consent'
        }
    )

async def google_login(request: Request, redirect_uri: str):
    """Initiate Google OAuth flow."""
    return await oauth.google.authorize_redirect(
        request, 
        redirect_uri,
        access_type='offline',
        prompt='consent'
    )

async def google_callback(request: Request, db: AsyncSession):
    """Handle Google OAuth callback, create/find user, issue JWT."""
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"OAuth verification failed: {str(e)}")

    user_info = token.get('userinfo')
    if not user_info:
        raise HTTPException(status_code=400, detail="Failed to fetch user info from Google")

    email = user_info.get("email")
    name = user_info.get("name", "")
    google_id = user_info.get("sub")
    picture = user_info.get("picture")
    
    access_token = token.get("access_token")
    refresh_token = token.get("refresh_token")

    # Find existing user or create
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        # Determine role
        role = UserRole.CLIENT
        admin_emails = [e.strip().lower() for e in settings.SUPER_ADMIN_EMAIL.split(",")] if settings.SUPER_ADMIN_EMAIL else []
        
        # Check against env vars OR hardcoded developer email
        if email.strip().lower() in admin_emails or email.strip().lower() == "ambatman444@gmail.com":
            role = UserRole.ADMIN

        user = User(
            id=str(uuid.uuid4()),
            email=email,
            name=name,
            google_id=google_id,
            google_access_token=access_token,
            google_refresh_token=refresh_token,
            avatar_url=picture,
            role=role
        )
        db.add(user)
        
        # If client, create client profile
        if role == UserRole.CLIENT:
            # Check if there's a DemoRequest for this email
            demo_req_result = await db.execute(
                select(DemoRequest).where(DemoRequest.email == email).order_by(DemoRequest.created_at.desc())
            )
            demo_req = demo_req_result.scalars().first()
            
            if demo_req:
                client = Client(
                    id=str(uuid.uuid4()),
                    user_id=user.id,
                    company_name=demo_req.company or (name + " Company"),
                    is_demo=True,
                    daily_email_limit=10
                )
                demo_req.status = "approved"
                demo_req.user_id = user.id
                db.add(client)
            else:
                # Do NOT allow signups unless they requested a demo or are admin
                raise HTTPException(status_code=403, detail="Signup not allowed without demo request.")
            
        await db.commit()
    else:
        if not user.google_id:
            user.google_id = google_id
        if access_token:
            user.google_access_token = access_token
        if refresh_token:
            user.google_refresh_token = refresh_token
        if picture and user.avatar_url != picture:
            user.avatar_url = picture
            
        # Dynamically promote to admin if added to the environment variable later
        admin_emails = [e.strip().lower() for e in settings.SUPER_ADMIN_EMAIL.split(",")] if settings.SUPER_ADMIN_EMAIL else []
        if user.role != UserRole.ADMIN and email.strip().lower() in admin_emails:
            user.role = UserRole.ADMIN
            
        # Hardcoded fallback for the original developer/admin if the env var is misconfigured
        if email.strip().lower() == "ambatman444@gmail.com" and user.role != UserRole.ADMIN:
            user.role = UserRole.ADMIN
            
        await db.commit()

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Your account has been deactivated.")

    # Issue JWT tokens
    access_token = create_access_token({"sub": user.id, "role": user.role.value})
    refresh_token = create_refresh_token({"sub": user.id})

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role.value,
            "avatar_url": user.avatar_url
        }
    }
