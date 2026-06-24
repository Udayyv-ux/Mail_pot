import asyncio
import os
import json
from groq import AsyncGroq
from dotenv import load_dotenv

load_dotenv()

async def test():
    try:
        client = AsyncGroq(api_key=os.getenv('GROQ_API_KEY'))
        print("Sending request to Groq...")
        res = await client.chat.completions.create(
            messages=[
                {'role':'system','content':'You are a helpful assistant. Output JSON.'},
                {'role':'user','content':'test'}
            ],
            model='llama-3.1-8b-instant',
            response_format={'type':'json_object'}
        )
        print("Success:", res.choices[0].message.content)
    except Exception as e:
        print("Error:", e)

asyncio.run(test())
