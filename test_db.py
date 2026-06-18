import asyncio
from backend.main import init_db
async def run():
    print('Starting...')
    await init_db()
    print('Done!')
asyncio.run(run())
