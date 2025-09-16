from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
import random
import string
import asyncio
import logging

app = FastAPI()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logger = logging.getLogger(__name__)

class LobbyManager:
    def __init__(self):
        self.matches = {}
        
    def generate_match_id(self):
        characters = string.ascii_letters + string.digits
        match_id = ''.join(random.choice(characters) for _ in range(6)).upper()
        logger.info(f"Generated new match ID: {match_id}")
        return match_id

class Player:
    def __init__(self, lobby_id, websocket, username):
        self.lobby_id = lobby_id
        self.websocket = websocket
        self.score = 1000
        self.username = username
        
    async def send_data(self, data):
        await self.websocket.send_json(data)
        logger.debug(f"Sent to {self.username}: {data}")
        
    async def receive_data(self):
        data = await self.websocket.receive_json()
        logger.debug(f"Received from {self.username}: {data}")
        return data
    
class Match:
    def __init__(self, id, time_per_question):
        self.host = None
        self.players = []
        self.id = id
        self.time_per_question = time_per_question
        logger.info(f"Created match {id} with {time_per_question}s per question")
        
    def generate_equation(self):
        equation = 4
        logger.info(f"Generated equation: {equation}")
        return equation
    
    async def collect_answers(self):
        logger.info(f"Collecting answers from {len(self.players)} players")
        
        tasks = {player: asyncio.create_task(player.receive_data()) for player in self.players}

        done, pending = await asyncio.wait(tasks.values(), timeout=self.time_per_question)

        answers = {}
        for player, task in tasks.items():
            if task in done:
                answers[player] = task.result()
            else:
                answers[player] = None
                task.cancel()
                logger.warning(f"Player {player.username} did not answer in time")
        
        logger.info(f"Collected answers: {answers}")
        return answers
    
    async def start_match(self, round_count):
        logger.info(f"Starting match {self.id} for {round_count} rounds")
        await asyncio.gather(*(player.send_data({"action": "game_started"}) for player in self.players))
        
        i = 0

        current_status = "waiting_for_round_start"

        while current_status != "game_ended":
            if current_status == "waiting_for_round_start":
                equation, answer = self.generate_equation()
                if self.host is not None:
                    await self.host.send_data({"action": "display_equation", "equation": equation})
                current_status = "waiting_for_host"

            elif current_status == "waiting_for_host":
                host_data = await self.host.websocket.receive_json()
                logger.info(f"Received host data: {host_data}")
                
                current_status = "waiting_for_round_end"
                
                round_results = await self.collect_answers()
                
                scores = self.check_answers(round_results, answer)
                                
                print("All player responses:", round_results)
                
                logger.info(f"Round {i+1} results: {scores}")
                
                if i < round_count:
                    await asyncio.gather(*(player.send_data({"action": "round_ended", "score": player.score}) for player in self.players))
                    await self.host.send_data({"action": "display_round_stats", "stats": scores})
                    
                    current_status = "waiting_for_round_start"
                    
                    i += 1
                else:
                    await asyncio.gather(*(player.send_data({"action": "game_ended", "score": player.score}) for player in self.players))
                    await self.host.send_data({"action": "game_ended", "stats": scores})
                    
                    current_status = "game_ended"    

    
    def check_answers(self, round_results, answer):
        scores = {}
        for player, data in round_results.items():
            if data and data.get("answer") == answer:
                min_score = 100
                max_score = 500
                t = data.get("time_took", 0) / self.time_per_question
                score = min_score + (max_score - min_score) * (1 - t)**2
                player.score += score
                scores[player.username] = score
                logger.info(f"Player {player.username} scored {score}")
        return scores



class Host:
    def __init__(self, lobby_id, websocket):
        self.lobby_id = lobby_id
        self.websocket = websocket
        
    async def send_data(self, data):
        await self.websocket.send_json(data)
        logger.debug(f"Sent to host: {data}")

lobby_manager = LobbyManager()


@app.get("/host_lobby")
async def get():
    id = lobby_manager.generate_match_id()
    lobby_manager.matches[id] = (Match(id, 10))
    return id

@app.websocket("/ws/{lobby_id}")
async def player_websocket_endpoint(websocket: WebSocket, lobby_id: str):
    await websocket.accept()
    username = await websocket.receive_json()["username"]
    logger.info(f"Player {username} connected to lobby {lobby_id}")
    if lobby_manager.matches.get(lobby_id) != None:
        lobby_manager.matches[lobby_id].players.append(Player(lobby_id, websocket, username))

@app.websocket("/ws/host_{lobby_id}")
async def host_websocket_endpoint(websocket: WebSocket, lobby_id: str):
    await websocket.accept()
    logger.info(f"Host connected to lobby {lobby_id}")
    if lobby_manager.matches.get(lobby_id) != None:
        lobby_manager.matches[lobby_id].host = Host(lobby_id, websocket)