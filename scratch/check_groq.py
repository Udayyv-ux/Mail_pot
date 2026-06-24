import asyncio
from backend.database import SessionLocal
from backend.models.client import Client
from sqlalchemy import select

async def check():
    async with SessionLocal() as db:
        c = await db.execute(select(Client))
        client = c.scalars().first()
        if client:
            print("Client Groq Key:", repr(client.groq_api_key))
        else:
            print("No client found.")

asyncio.run(check())
