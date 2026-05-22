import asyncio
import os
import sys

sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv("job-portal/.env")
import os, sys
sys.path.insert(0, "job-portal")

from openai import AsyncOpenAI


async def test():
    api_key = os.getenv("OPENAI_API_KEY")
    print("API key loaded:", bool(api_key), "| starts with:", api_key[:10] if api_key else "NONE")

    client = AsyncOpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )
    try:
        r = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Return JSON: {\"message\": \"hello\"}"}],
            response_format={"type": "json_object"},
        )
        print("SUCCESS:", r.choices[0].message.content)
    except Exception as e:
        print("ERROR:", type(e).__name__, str(e))


asyncio.run(test())
