"""
Template management API routes for clients.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import json

from backend.database import get_db
from backend.middleware.auth_middleware import require_client
from backend.models.client import Client
from backend.models.template import Template

router = APIRouter(prefix="/api/client/templates", tags=["templates"])

async def get_client_id(user, db: AsyncSession):
    result = await db.execute(select(Client.id).where(Client.user_id == user.id))
    client_id = result.scalar_one_or_none()
    if not client_id:
        raise HTTPException(404, "Client profile not found")
    return client_id

@router.get("")
async def list_templates(db: AsyncSession = Depends(get_db), current_user = Depends(require_client)):
    client_id = await get_client_id(current_user, db)
    result = await db.execute(select(Template).where(Template.client_id == client_id).order_by(Template.created_at.desc()))
    return result.scalars().all()

class TemplateCreate(BaseModel):
    project_name: str
    subject: str
    body_html: str
    image_urls_json: str = "[]"
    banner_url: str | None = None
    whatsapp_template_name: str | None = None

@router.post("")
async def create_template(data: TemplateCreate, db: AsyncSession = Depends(get_db), current_user = Depends(require_client)):
    client_id = await get_client_id(current_user, db)
    
    # Check plan limits (simplified for now)
    
    template = Template(
        client_id=client_id,
        project_name=data.project_name,
        subject=data.subject,
        body_html=data.body_html,
        image_urls_json=data.image_urls_json,
        banner_url=data.banner_url,
        whatsapp_template_name=data.whatsapp_template_name
    )
    db.add(template)
    await db.commit()
    return template

@router.put("/{id}")
async def update_template(id: str, data: TemplateCreate, db: AsyncSession = Depends(get_db), current_user = Depends(require_client)):
    client_id = await get_client_id(current_user, db)
    
    result = await db.execute(select(Template).where(Template.id == id, Template.client_id == client_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(404, "Template not found")
        
    template.project_name = data.project_name
    template.subject = data.subject
    template.body_html = data.body_html
    template.image_urls_json = data.image_urls_json
    template.banner_url = data.banner_url
    template.whatsapp_template_name = data.whatsapp_template_name
    
    await db.commit()
    return template

@router.delete("/{id}")
async def delete_template(id: str, db: AsyncSession = Depends(get_db), current_user = Depends(require_client)):
    client_id = await get_client_id(current_user, db)
    
    result = await db.execute(select(Template).where(Template.id == id, Template.client_id == client_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(404, "Template not found")
        
    await db.delete(template)
    await db.commit()
    return {"status": "success"}
