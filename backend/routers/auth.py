"""
Authentication routes.
"""
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.services.auth_service import google_login, google_callback
from backend.middleware.auth_middleware import get_current_user
from backend.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.get("/google")
async def login_google(request: Request):
    """Initiate Google OAuth."""
    # Force the redirect URI to use the APP_URL defined in settings
    # This prevents 'redirect_uri_mismatch' errors when deployed behind a reverse proxy (like Railway)
    # which might downgrade the scheme to http instead of https.
    redirect_uri = f"{settings.APP_URL}/api/auth/callback"
    return await google_login(request, redirect_uri)

@router.get("/callback")
async def auth_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """Google OAuth callback."""
    try:
        result = await google_callback(request, db)
    except HTTPException as e:
        if e.status_code == 403:
            return RedirectResponse(url="/?error=unauthorized_signup")
        raise e
    
    access_token = result["access_token"]
    refresh_token = result["refresh_token"]
    role = result["user"]["role"]
    
    # Redirect back to frontend
    # In a real app you might want to use a state parameter to remember where they came from
    portal_path = "/admin/" if role == "admin" else "/client/"
    
    redirect_url = f"{portal_path}?token={access_token}&refresh={refresh_token}"
    return RedirectResponse(redirect_url)

@router.get("/me")
async def get_me(current_user = Depends(get_current_user)):
    """Get current user profile."""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role.value,
        "avatar_url": current_user.avatar_url
    }

@router.post("/refresh")
async def refresh_token():
    """Placeholder for token refresh."""
    # To implement: decode refresh token, verify it, issue new access token
    raise HTTPException(status_code=501, detail="Not implemented")

from pydantic import BaseModel
from sqlalchemy import select
from passlib.context import CryptContext
from backend.models.user import User, UserRole
from backend.middleware.auth_middleware import create_access_token, create_refresh_token

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class BasicLogin(BaseModel):
    email: str
    password: str

@router.post("/login/basic")
async def login_basic(data: BasicLogin, db: AsyncSession = Depends(get_db)):
    """Basic login for sub-admins using username and password."""
    result = await db.execute(select(User).where(User.email == data.email.strip().lower()))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    if user.role != UserRole.SUB_ADMIN:
        raise HTTPException(status_code=403, detail="Basic login is only available for sub-admins. Please use Google Sign-In.")
        
    if not user.hashed_password or not pwd_context.verify(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
        
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is disabled")

    # Generate tokens
    user_data = {
        "sub": user.id,
        "email": user.email,
        "role": user.role.value
    }
    
    access_token = create_access_token(user_data)
    refresh_token = create_refresh_token(user_data)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role.value
        }
    }
