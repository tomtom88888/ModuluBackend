import asyncio
import json
import websockets
import random

async def tournament_player(tournament_id: str, username: str):
    uri = f"ws://localhost:8000/ws/{tournament_id}"

    try:
        async with websockets.connect(uri) as websocket:
            await websocket.send(json.dumps({"username": username}))
            print(f"✅ {username} joined tournament {tournament_id}")

            async def receive_messages():
                while True:
                    try:
                        msg = await websocket.recv()
                        data = json.loads(msg)
                        state = data.get("state")

                        if state == "ping":
                            continue
                        elif state == "prep_tournament":
                            print(f"🕹️ [{username}] Waiting for tournament to start...")
                        elif state == "prep_match":
                            print(f"⚙️ [{username}] Preparing for match...")
                        elif state == "round_ongoing":
                            correct_answer = random.choice([True, False])
                            print("Data: " + str(data))

                            if correct_answer:
                                answer = data.get("answer")
                            else:
                                answer = str(random.randint(1, 100))
                            
                            time_took = round(random.uniform(0.5, 6.0))
                            
                            await asyncio.sleep(time_took)
                            
                            print(f"⏱️ [{username}] Match started! Submitting answer: {answer}")
                            await websocket.send(json.dumps({
                                "username": username,
                                "answer": answer,
                                "time_took": time_took
                            }))
                        elif state == "round_ended":
                            print(f"🏁 [{username}] Match ended! Score: {data.get('score', '?')}")
                        elif state == "game_over":
                            print(f"🎉 [{username}] Tournament ended! Final data:")
                            print(json.dumps(data, indent=2))
                            return
                        else:
                            print(f"📩 [{username}] Message: {data}")

                    except websockets.exceptions.ConnectionClosed:
                        print(f"❌ [{username}] Disconnected.")
                        break

            await receive_messages()

    except Exception as e:
        print(f"⚠️ Error for {username}: {e}")


async def main():
    tournament_id = input("Enter the tournament ID: ").strip()
    base_name = input("Enter base username: ").strip()
    client_number = int(input("Enter how many test clients you want to run: ").strip())

    players = [f"{base_name}{i}" for i in range(1, client_number + 1)]

    await asyncio.gather(*(tournament_player(tournament_id, name) for name in players))


if __name__ == "__main__":
    asyncio.run(main())
