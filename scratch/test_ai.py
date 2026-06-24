import asyncio
import os
from groq import AsyncGroq
from dotenv import load_dotenv
import json

load_dotenv()

async def test_ai():
    print("Testing Groq AI generation...")
    try:
        groq_key = os.getenv("GROQ_API_KEY")
        if not groq_key:
            print("No GROQ_API_KEY found in .env")
            return
            
        ai_client = AsyncGroq(api_key=groq_key)
        
        system_prompt = (
            "You are an expert cold email copywriter. The user will give you a goal for their campaign. "
            "Generate a highly converting email template. "
            "Return ONLY a JSON object with two keys: 'subject' (a catchy subject line) and 'html_body' (the HTML formatted email body with basic styling, use {first_name} for personalization)."
        )

        response = await ai_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "A welcome email for new users of a SaaS product."}
            ],
            model="llama-3.1-8b-instant",
            temperature=0.7,
            response_format={"type": "json_object"}
        )
        
        result_str = response.choices[0].message.content
        data = json.loads(result_str)
        print("Success!")
        print("--- Subject ---")
        print(data.get('subject'))
        print("--- Body ---")
        print(data.get('html_body'))
        
    except Exception as e:
        print(f"Error: {str(e)}")

asyncio.run(test_ai())
