"""
Authentication routes.
"""
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from backend.database import get_db
from backend.services.auth_service import google_login, google_callback
from backend.middleware.auth_middleware import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.get("/google")
async def login_google(request: Request):
    """Initiate Google OAuth."""
    redirect_uri = str(request.url_for('auth_callback'))
    # If testing locally behind a proxy, you might need to force http/https
    # redirect_uri = redirect_uri.replace("http://", "https://")
    return await google_login(request, redirect_uri)

@router.get("/callback")
async def auth_callback(request: Request, db: AsyncSession = Depends(get_db)):
    """Google OAuth callback."""
    result = await google_callback(request, db)
    
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
