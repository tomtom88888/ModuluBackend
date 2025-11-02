import asyncio
import json
import requests
import websockets

API_BASE = "http://192.168.1.27:8000"
WS_BASE = "ws://192.168.1.27:8000"

def create_lobby():
    """Create a new lobby via FastAPI /host_lobby endpoint."""
    response = requests.get(f"{API_BASE}/host_lobby")
    response.raise_for_status()
    lobby_id = response.json()
    print(f"✅ Created lobby with ID: {lobby_id}")
    return lobby_id


async def send_pings(websocket, stop_event):
    """Send ping messages until Enter is pressed."""
    while not stop_event.is_set():
        ping_msg = {"state": "waiting"}
        await websocket.send(json.dumps(ping_msg))
        print("📤 Sent ping")
        await asyncio.sleep(1)  # adjust interval as needed


async def wait_for_enter(stop_event):
    """Wait for Enter key to stop the ping loop."""
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, input, "Press Enter to start...\n")
    stop_event.set()
    print("⏩ Enter pressed, stopping pings...")


async def run_host(lobby_id: str):
    """Connect as host and start the game."""
    ws_url = f"{WS_BASE}/ws/host/{lobby_id}"
    print(f"🔗 Connecting to {ws_url}...")

    async with websockets.connect(ws_url) as websocket:
        print("✅ Connected as host!")

        # Create an event to stop the ping loop
        stop_event = asyncio.Event()

        # Start pinging and waiting for Enter in parallel
        ping_task = asyncio.create_task(send_pings(websocket, stop_event))
        enter_task = asyncio.create_task(wait_for_enter(stop_event))

        # Wait until Enter is pressed
        await enter_task

        # Send the start message
        start_msg = {"state": "start_game"}
        await websocket.send(json.dumps(start_msg))
        print(f"📤 Sent: {start_msg}")

        # Stop the ping loop
        ping_task.cancel()
        try:
            await ping_task
        except asyncio.CancelledError:
            pass

        # Handle messages from the server
        try:
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                print(f"📥 Received: {data}")

                if data.get("state") == "display_equation":
                    print(f"📝 Equation to display: {data['equation']}")
                    await asyncio.sleep(5)

                    start_round = {"state": "start_round"}
                    await websocket.send(json.dumps(start_round))
                    print(f"📤 Sent: {start_round}")

                elif data.get("state") == "display_round_stats":
                    print(f"📊 Round stats: {data['stats']}")

                elif data.get("state") == "game_ended":
                    print(f"🏁 Game ended! Final stats: {data['stats']}")
                    break

        except websockets.ConnectionClosed as e:
            print(f"⚠️ Connection closed: {e}")


if __name__ == "__main__":
    lobby_id = create_lobby()
    asyncio.run(run_host(lobby_id))
