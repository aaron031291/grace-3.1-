import asyncio
import app

async def run():
    async with app.lifespan(app.app):
        print('Lifespan running successfully')
        await asyncio.sleep(2)

if __name__ == '__main__':
    asyncio.run(run())
