from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import random
import string
import asyncio
import logging
from equation_generator import *
from powerups import *

app = FastAPI()

KEEP_ALIVE_INTERVAL = 20
TIME_PER_QUESTION = 20
IDLE_TIMEOUT = 3600

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1", "*"],  # <-- use wildcard in dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)

class Tournament:
    def __init__(self, id):
        self.id = id
        self.player = []
        self.matches = []
    
    async def start_game(self):
        winners = []
        
        
        
        for match in self.matches:
            winners.append(await match.start_match())
        left_over_players = winners % 3

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
        self.place = 1
        self.active_powerup = None
        self.active_attack = None
        self.is_correct = False
        
    async def send_data(self, data):
        await self.websocket.send_json(data)
        logger.debug(f"Sent to {self.username}: {data}")
        
    async def receive_data(self):
        data = await self.websocket.receive_json()
        logger.debug(f"Received from {self.username}: {data}")
        return data
    
    async def start_keep_alive(self, interval: int = 20):
        async def ping():
            try:
                while True:
                    await self.websocket.send_json({"type": "ping"})
                    await asyncio.sleep(interval)
            except Exception:
                logger.info(f"Player {self.username} disconnected")
                pass

        self.keep_alive_task = asyncio.create_task(ping())
    
class Match:
    def __init__(self, id, time_per_question):
        self.host = None
        self.players = []
        self.id = id
        self.time_per_question = time_per_question
        self.answer = 0
        logger.info(f"Created match {id} with {time_per_question}s per question")
    
    def assign_player_places(self):
        sorted_players = sorted(self.players, key=lambda p: p.score, reverse=True)
    
        for i, player in enumerate(sorted_players):
            player.place = i + 1
    
    def generate_equation(self):
        equation, answer = generate_arithmetic(difficulty="medium")
        self.answer = answer
        return equation, answer
    
    async def collect_powerups(self):
        logger.info(f"Collecting powerups from {len(self.players)} players")
        
        tasks = {player: asyncio.create_task(player.receive_data()) for player in self.players}
        done, _ = await asyncio.wait(tasks.values(), timeout=5)

        powerups = {}
        for player, task in tasks.items():
            if task in done:
                try:
                    data = task.result()
                except Exception:
                    data = None
            else:
                task.cancel()
                data = None
                logger.warning(f"Player {player.username} did not send powerup in time")

            if data and data.get("powerup") in POWERUPS:
                player.active_powerup = POWERUPS[data["powerup"]]
                powerups[player] = data
            else:
                player.active_powerup = None
                powerups[player] = {"powerup": "none"}

        logger.info(f"Collected powerups: {powerups}")
        return powerups
    
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
    
    async def start_match(self, round_count: int):
        logger.info(f"Starting match {self.id} for {round_count} rounds")
        
        current_status = "waiting_for_round_start"
        round_index = 0

        while current_status != "game_ended":
            if current_status == "waiting_for_round_start":
                await  asyncio.sleep(5)
                current_status = await self.handle_round_start()
                
            elif current_status == "waiting_for_host":
                current_status = await self.handle_host_phase(round_index, round_count)
                round_index += 1
            elif current_status == "waiting_for_round_end":
                # round_end handled in host phase
                pass
            
            round_index += 1


        winner = max(self.players, key=lambda p: p.score)
        return winner


    async def broadcast(self, state=None, **extra):
        data = {"state": state, **extra} if state else extra
        await asyncio.gather(*(p.send_data(data) for p in self.players), return_exceptions=True)

    async def handle_round_start(self):
        equation, answer = self.generate_equation()
        logger.info(f"Equation: {equation}, Answer: {answer}")

        if self.host:
            await self.host.send_data({"state": "prep_round", "equation": equation})

        await self.broadcast("prep_round")
        return "waiting_for_host"

    async def handle_host_phase(self, round_index, total_rounds):
        # powerups = await self.collect_powerups()
        # await self.handle_start_powerups(powerups)
        
        host_data = {}
        try:
            while host_data.get("state") != "started_round":
                host_data = await self.host.websocket.receive_json()
                logger.info(f"Received data from host: {host_data}")
        except Exception as e:
            logger.warning(f"Host disconnected unexpectedly: {e}")
            return "game_ended"
        
        logger.info(f"Received host data: {host_data}")

        await self.broadcast("round_started")
        await self.host.send_data({"state": "round_started", "current_round": round_index})
        
        round_results = await self.collect_answers()

        scores = self.check_answers(round_results, self.answer)
        # self.handle_end_powerups(powerups, scores)
        self.assign_player_places()

        logger.info(f"Round {round_index + 1} results: {scores}")

        if round_index < total_rounds - 1:
            await self.round_end_phase(scores)
            return "waiting_for_round_start"
        else:
            await self.end_game(scores)
            return "game_ended"
        
    async def handle_start_powerups(self, powerups):
        for player, data in powerups.items():
            powerup = POWERUPS.get(data.get("powerup"))
            if not powerup:
                continue
            
            if powerup.state == PowerUpState.ROUND_START:
                effect_data = {
                    "player": player,
                    "powerup": data.get("powerup")
                }
                
                target_username = data.get("target_player")
                if target_username:
                    effect_data["target_player"] = next(
                        (p for p in self.players if p.username == target_username), None
                    )
                
                try:
                    powerup.effect(effect_data)
                except Exception as e:
                    logger.error(f"Error running {powerup.name}: {e}")
                
    async def handle_end_powerups(self, powerups, scores):
        for player, data in powerups.items():
            if not data or data.get("powerup") == "none":
                continue

            powerup_name = data.get("powerup")
            powerup = POWERUPS.get(powerup_name)
            if not powerup or powerup.state != PowerUpState.ROUND_END:
                continue

            effect_data = {
                "player": player,
                "powerup": powerup_name,
                "scores": scores
            }

            target_username = data.get("target_player")
            if target_username:
                effect_data["target_player"] = next(
                    (p for p in self.players if p.username == target_username),
                    None
                )

            try:
                powerup.effect(effect_data)
            except Exception as e:
                logger.error(f"Error running {powerup_name}: {e}")

    async def round_end_phase(self, scores):
        await self.broadcast_round_data()
        await self.host.send_data({"state": "round_ended", "stats": scores})
        
    async def broadcast_round_data(self):
        await asyncio.gather(*(p.send_data({"state": "round_ended", "score": p.score, "place": p.place }) for p in self.players))

    async def end_game(self, scores):
        """End the match and send final results."""
        await self.broadcast({
            "state": "game_ended",
            **{ "score": p.score for p in self.players }
        })
        await self.host.send_data({"state": "game_ended", "stats": scores})

    
    def check_answers(self, round_results, answer):
        scores = {}
        for player, data in round_results.items():
            logger.info(f"Player {player.username} Data {data}")
            try:
                if data is not None and int(data.get("answer")) == answer:
                    player.is_correct = True
                    min_score = 100
                    max_score = 500
                    t = data.get("time_took", 0) / self.time_per_question
                    score = round(min_score + (max_score - min_score) * (1 - t)**2)
                    player.score += score
                    scores[player.username] = player.score
                    
                    logger.info(f"Player {player.username} scored {score}")
                else:
                    player.is_correct = False
                    scores[player.username] = player.score
                    logger.info(f"Player {player.username} did not answer correctly")
            except (TypeError, ValueError):
                player.is_correct = False
                scores[player.username] = player.score
                logger.info(f"Player {player.username} did not answer correctly")
                continue
        
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
    logger.info(f"Host lobby request")
    lobby_manager.matches[id] = (Match(id, TIME_PER_QUESTION))
    return id

@app.websocket("/ws/{lobby_id}")
async def player_websocket_endpoint(websocket: WebSocket, lobby_id: str):
    await websocket.accept()
    if lobby_manager.matches.get(lobby_id) != None:
        username = (await websocket.receive_json())["username"]

        player = Player(lobby_id, websocket, username)
        
        logger.info(f"Player {username} connected to lobby {lobby_id}")
        
        await player.start_keep_alive(KEEP_ALIVE_INTERVAL)
        
        lobby_manager.matches[lobby_id].players.append(player)
        player_names = [p.username for p in lobby_manager.matches[lobby_id].players]
        await lobby_manager.matches[lobby_id].host.send_data({"state": "prep_game", "players": player_names})
        await websocket.send_json({"state": "prep_game"})
        
        try:
            while True:
                await asyncio.sleep(IDLE_TIMEOUT)
        except Exception:
            logger.info(f"Player {username} disconnected")
        finally:
            match = lobby_manager.matches.get(lobby_id)
            if match and player in match.players:
                match.players.remove(player)
            if hasattr(player, "keep_alive_task"):
                player.keep_alive_task.cancel()
    else:
        await websocket.close()
            
@app.websocket("/ws/host/{lobby_id}")
async def host_websocket_endpoint(websocket: WebSocket, lobby_id: str):
    await websocket.accept()
    logger.info(f"Host connected to lobby {lobby_id}")
    if lobby_manager.matches.get(lobby_id) != None:
        lobby_manager.matches[lobby_id].host = Host(lobby_id, websocket)
        while True:
            data = await websocket.receive_json()
            if data["state"] == "start_game":
                await websocket.send_json({"state": "starting_game", "max_rounds": 5, "time_per_question": TIME_PER_QUESTION})
                logger.info(f"Starting match in lobby {lobby_id}")
                await lobby_manager.matches[lobby_id].start_match(3)
                break
        try:
            while True:
                await asyncio.sleep(IDLE_TIMEOUT)
        except Exception as e:
            logger.info(f"Host disconnected: {e}")
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )