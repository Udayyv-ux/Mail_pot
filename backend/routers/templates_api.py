"""
Template management API routes for clients.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import json

from backend.database import get_db
from backend.middleware.auth_middleware import require_client, require_active_subscription
from backend.models.client import Client
from backend.models.template import Template
from backend.models.plan import Plan
from backend.config import settings
from groq import AsyncGroq

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
async def create_template(data: TemplateCreate, db: AsyncSession = Depends(get_db), current_user = Depends(require_active_subscription)):
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
    return {"status": "success", "id": template.id}

@router.put("/{id}")
async def update_template(id: str, data: TemplateCreate, db: AsyncSession = Depends(get_db), current_user = Depends(require_active_subscription)):
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
    return {"status": "success", "id": template.id}

@router.delete("/{id}")
async def delete_template(id: str, db: AsyncSession = Depends(get_db), current_user = Depends(require_active_subscription)):
    client_id = await get_client_id(current_user, db)
    
    result = await db.execute(select(Template).where(Template.id == id, Template.client_id == client_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(404, "Template not found")
        
    await db.delete(template)
    await db.commit()
    return {"status": "success"}


class AIGenerateRequest(BaseModel):
    prompt: str

@router.post("/generate")
async def generate_template(req: AIGenerateRequest, db: AsyncSession = Depends(get_db), current_user = Depends(require_active_subscription)):
    client_id = await get_client_id(current_user, db)
    
    # 1. Verify Plan Access
    client = await db.get(Client, client_id)
    plan = await db.get(Plan, client.plan_id) if client.plan_id else None
    
    from backend.models.user import UserRole
    if current_user.role != UserRole.ADMIN:
        if not plan or not getattr(plan, 'has_ai_templates', False):
            raise HTTPException(403, "Your plan does not support AI Generated Templates. Please upgrade to unlock this feature.")
            
        # Check daily AI limit
        # Reset if new day
        from datetime import datetime, timezone
        today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if client.last_reset_date != today_str:
            client.emails_sent_today = 0
            client.ai_requests_today = 0
            client.last_reset_date = today_str
            
        ai_limit = getattr(plan, 'ai_limit', -1)
        if ai_limit != -1 and client.ai_requests_today >= ai_limit:
            raise HTTPException(429, f"You have reached your daily AI usage limit of {ai_limit} requests.")
            
        # Increment usage
        client.ai_requests_today += 1
        await db.commit()
        
    # 2. Get AI API Key
    groq_key = getattr(client, 'groq_api_key', None) or settings.GROQ_API_KEY
    if not groq_key:
        raise HTTPException(500, "AI Service is not configured")
        
    # 3. Call AI
    ai_client = AsyncGroq(api_key=groq_key)
    
    system_prompt = (
        "You are an expert cold email copywriter. The user will give you a goal for their campaign. "
        "Generate a highly converting email template. "
        "Return the output in STRICT JSON format with exactly two keys: 'subject' and 'html_body'. "
        "The 'html_body' MUST be formatted using HTML tags (e.g. <p>, <br>, <strong>). "
        "Use {first_name} or {Company} as placeholders for personalization. "
        "Do not output markdown code blocks like ```json, JUST output the raw JSON."
    )
    
    try:
        response = await ai_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": req.prompt}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```json"):
            content = content.split("```json")[1].split("```")[0].strip()
        elif content.startswith("```"):
            content = content.split("```")[1].split("```")[0].strip()
            
        import json
        return json.loads(content)
    except Exception as e:
        print(f"Groq API Error: {e}")
        raise HTTPException(500, f"AI Generation failed: {str(e)}")
