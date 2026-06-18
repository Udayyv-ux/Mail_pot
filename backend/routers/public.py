"""
Public API routes for landing page (no auth required).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from backend.database import get_db
from backend.models.plan import Plan
from backend.models.app_settings import Policy, AppSetting, DemoRequest

router = APIRouter(prefix="/api/public", tags=["public"])

@router.get("/plans")
async def get_active_plans(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Plan).where(Plan.is_active == True).order_by(Plan.price_monthly.asc()))
    return result.scalars().all()

@router.get("/policies")
async def list_policies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Policy).where(Policy.is_active == True))
    return result.scalars().all()

@router.get("/policies/{slug}")
async def get_policy(slug: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Policy).where(Policy.slug == slug, Policy.is_active == True))
    policy = result.scalar_one_or_none()
    if not policy:
        raise HTTPException(404, "Policy not found")
    return policy

class DemoSubmit(BaseModel):
    name: str
    email: str
    company: str = ""
    phone: str = ""
    message: str = ""

@router.post("/demo-request")
async def submit_demo(data: DemoSubmit, db: AsyncSession = Depends(get_db)):
    demo = DemoRequest(**data.model_dump())
    db.add(demo)
    await db.commit()
    return {"status": "success"}

@router.get("/settings")
async def get_public_settings(db: AsyncSession = Depends(get_db)):
    # Only return branding and landing categories
    result = await db.execute(select(AppSetting).where(AppSetting.category.in_(["branding", "landing"])))
    settings_list = result.scalars().all()
    
    # Format as key-value dict
    return {s.key: s.value for s in settings_list}
