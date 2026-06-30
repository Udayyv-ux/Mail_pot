"""
JWT authentication middleware and role-based access control.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.database import get_db
from backend.models.user import User, UserRole
from backend.models.client import Client

security = HTTPBearer(auto_error=False)


# ── Token Creation ───────────────────────────────────────────────────────────

def create_access_token(data: dict) -> str:
    """Create a short-lived access token."""
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["type"] = "access"
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a long-lived refresh token."""
    to_encode = data.copy()
    to_encode["exp"] = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode["type"] = "refresh"
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── Dependencies ─────────────────────────────────────────────────────────────

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and verify user from JWT. Returns the User ORM object."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return user


async def require_super_admin(user: User = Depends(get_current_user)) -> User:
    """Restrict endpoint strictly to the super admin."""
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Super Admin access required")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Restrict endpoint to admin and sub-admin users."""
    if user.role not in (UserRole.ADMIN, UserRole.SUB_ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


async def require_client(user: User = Depends(get_current_user)) -> User:
    """Restrict endpoint to client, demo, or admin users (admins need access to test the client portal)."""
    if user.role not in (UserRole.CLIENT, UserRole.DEMO, UserRole.ADMIN, UserRole.SUB_ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Client access required")
    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Same as get_current_user but returns None instead of raising if not authenticated."""
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None

async def require_active_subscription(
    user: User = Depends(require_client),
    db: AsyncSession = Depends(get_db)
) -> User:
    """Restrict endpoint to users with an active trial or paid subscription."""
    # Admins bypass
    if user.role == UserRole.ADMIN:
        return user
        
    result = await db.execute(select(Client).where(Client.user_id == user.id))
    client = result.scalar_one_or_none()
    
    if not client:
        raise HTTPException(status_code=403, detail="Client profile not found")
        
    now = datetime.now(timezone.utc)
    
    # Check subscription first
    if client.subscription_ends_at and client.subscription_ends_at > now:
        return user
        
    # Check if admin assigned a plan manually (lifetime / no expiration)
    if client.plan_id and not client.subscription_ends_at:
        return user
        
    # Check trial
    if client.trial_ends_at and client.trial_ends_at > now:
        return user
        
    raise HTTPException(status_code=402, detail="Trial or Subscription Expired")
