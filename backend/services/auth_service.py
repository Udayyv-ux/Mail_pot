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
        client_kwargs={'scope': 'openid email profile'}
    )

async def google_login(request: Request, redirect_uri: str):
    """Initiate Google OAuth flow."""
    return await oauth.google.authorize_redirect(request, redirect_uri)

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

    # Find existing user or create
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        # Determine role
        role = UserRole.CLIENT
        admin_email = settings.SUPER_ADMIN_EMAIL.strip().lower() if settings.SUPER_ADMIN_EMAIL else ""
        if admin_email and email.strip().lower() == admin_email:
            role = UserRole.ADMIN

        user = User(
            id=str(uuid.uuid4()),
            email=email,
            name=name,
            google_id=google_id,
            avatar_url=picture,
            role=role
        )
        db.add(user)
        
        # If client, create client profile
        if role == UserRole.CLIENT:
            client = Client(
                id=str(uuid.uuid4()),
                user_id=user.id,
                company_name=name + " Company"
            )
            db.add(client)
            
        await db.commit()
    else:
        # Update details if needed
        if not user.google_id:
            user.google_id = google_id
        if picture and user.avatar_url != picture:
            user.avatar_url = picture
            
        # Dynamically upgrade to admin if email matches
        admin_email = settings.SUPER_ADMIN_EMAIL.strip().lower() if settings.SUPER_ADMIN_EMAIL else ""
        if admin_email and email.strip().lower() == admin_email and user.role != UserRole.ADMIN:
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
