import asyncio
from backend.database import SessionLocal
from backend.models.client import Client
from sqlalchemy import select

async def get():
    async with SessionLocal() as db:
        c = await db.execute(select(Client))
        client = c.scalars().first()
        if client:
            print(f'Phone ID: {client.whatsapp_phone_number_id}')
            print(f'WABA ID: {client.whatsapp_business_account_id}')
            print(f'App ID: {client.meta_app_id}')
        else:
            print('Client not found')

asyncio.run(get())
