import re

templates_api_path = r"C:\Users\Uday\Documents\GitHub\Mail_pot\backend\routers\templates_api.py"
with open(templates_api_path, "r", encoding="utf-8") as f:
    content = f.read()

# Add imports if missing
if "from backend.models.plan import Plan" not in content:
    content = content.replace(
        "from backend.models.template import Template",
        "from backend.models.template import Template\nfrom backend.models.plan import Plan\nfrom backend.config import settings\nfrom groq import AsyncGroq"
    )

new_endpoint = """
class AIGenerateRequest(BaseModel):
    prompt: str

@router.post("/generate")
async def generate_template(req: AIGenerateRequest, db: AsyncSession = Depends(get_db), current_user = Depends(require_active_subscription)):
    client_id = await get_client_id(current_user, db)
    
    # 1. Verify Plan Access
    client = await db.get(Client, client_id)
    plan = await db.get(Plan, client.plan_id) if client.plan_id else None
    
    if not plan or not getattr(plan, 'has_ai_templates', False):
        raise HTTPException(403, "Your plan does not support AI Generated Templates. Please upgrade to unlock this feature.")
        
    # 2. Get AI API Key
    groq_key = client.groq_api_key if client.groq_api_key else settings.GROQ_API_KEY
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
            temperature=0.7
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
"""

if "@router.post(\"/generate\")" not in content:
    content += "\n" + new_endpoint
    with open(templates_api_path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Updated templates_api.py")
