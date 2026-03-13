import asyncio
import websockets

async def test_ws():
    uri = "ws://localhost:8000/dashboard"
    try:
        print(f"Connecting to {uri}...")
        async with websockets.connect(uri) as ws:
            print("Connected! Waiting 2 seconds...")
            await asyncio.sleep(2)
            print("Disconnecting cleanly.")
    except Exception as e:
        print(f"Failed: {e}")

asyncio.run(test_ws())
