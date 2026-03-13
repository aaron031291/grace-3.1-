import json
import asyncio
from backend.cognitive.proactive_healing_engine import get_proactive_engine

async def main():
    try:
        engine = get_proactive_engine()
        immune = engine._get_immune()
        res = immune.scan()
        print(json.dumps(res))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
