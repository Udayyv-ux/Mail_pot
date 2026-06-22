import asyncio
from backend.database import SessionLocal
from backend.models.email_log import EmailLog
from backend.models.template import Template
from sqlalchemy import select

async def run():
    async with SessionLocal() as db:
        print("--- RECENT LOGS ---")
        res = await db.execute(select(EmailLog).order_by(EmailLog.sent_at.desc()).limit(15))
        for l in res.scalars().all():
            print(f"To: {l.recipient_email}, AI Category: {l.category_assigned}, Template: {l.template_used}")
            
        print("\n--- TEMPLATES ---")
        res2 = await db.execute(select(Template).where(Template.is_active == True))
        for t in res2.scalars().all():
            print(f"ID: {t.id}, Project Name: {t.project_name}, Subject: {t.subject}")

asyncio.run(run())
