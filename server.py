from __future__ import annotations
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import random
import string
import asyncio
import logging
import math
from typing import Dict, List, Optional, Any, Tuple

from equation_generator import generate_arithmetic
from powerups import POWERUPS, PowerUpState

app = FastAPI()

KEEP_ALIVE_INTERVAL: int = 20
TIME_PER_QUESTION: int = 20
IDLE_TIMEOUT: int = 3600

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://127.0.0.1", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger(__name__)


class TournamentConfig:
    def __init__(self, time_per_question):
        self.time_per_question = time_per_question


class Tournament:
    def __init__(self, id: str) -> None:
        self.id: str = id
        self.players: List[Player] = []
        self.houses: List[House] = []
        self.host: Host = None
        self.config = TournamentConfig(30)

    def assign_players_to_houses(self, players: List[Player]):
        players_copy = players.copy()
        player_count = len(players_copy)

        if player_count >= 9:
            full_groups_of_9 = player_count // 9
            house_amount = full_groups_of_9 * 3

            if player_count % 9 >= 6:
                house_amount += 2

            for _ in range(house_amount):
                self.houses.append(House(self.host, players_copy[:3], self.config))
                del players_copy[:3]

            for player in players_copy:
                random.choice(self.houses).players.append(player)

        else:
            if player_count >= 6:
                self.houses.append(House(self.host, players_copy[:3], self.config))
                self.houses.append(House(self.host, players_copy[3:], self.config))
            else:
                self.houses.append(House(self.host, players_copy, self.config))
        

    async def start_tournament(self):
        current_players = self.players.copy()
        random.shuffle(current_players)
        

        while len(current_players) >= 3:
            self.houses.clear()
            self.assign_players_to_houses(current_players)

            winners: List[Player] = []
            
            for house in self.houses:
                await self.host.send_data({
                    "state": "prep_game",
                    "players": [p.to_json() for p in house.players]
                })
                
                await asyncio.sleep(3)

                winner: Player = await house.start_match(round_count=5)
                winners.append(winner)
                
                for player in house.players:
                    player.score = 1000
                
            current_players = winners
            
        return current_players[0]

    
    async def broadcast(self, state: Optional[str] = None, **extra: Any) -> None:
        data = {"state": state, **extra} if state else extra
        await asyncio.gather(*(p.send_data(data) for p in self.players), return_exceptions=True)
    
    async def prepare_game(self) -> None:
        await self.broadcast(state="waiting_for_game")
        await self.host.send_data({
            "state": "starting_game",
            "tournament_info": {"max_houses": len(self.houses), "time_per_question": TIME_PER_QUESTION, "max_rounds": 5, "players": [[player.to_json() for player in house.players] for house in self.houses]}
        })
    

class LobbyManager:
    def __init__(self) -> None:
        self.tournaments: Dict[str, Tournament] = {}
        self.matches: Dict[str, House] = {}

    def generate_id(self) -> str:
        characters: str = string.ascii_letters + string.digits
        id: str = ''.join(random.choice(characters) for _ in range(6)).upper()
        logger.info(f"Generated new ID: {id}")
        return id


class Player:
    def __init__(self, websocket: WebSocket, username: str) -> None:
        self.websocket: WebSocket = websocket
        self.score: int = 1000
        self.username: str = username
        self.place: int = 1
        self.active_powerup: Optional[Any] = None
        self.active_attack: Optional[Any] = None
        self.is_correct: bool = False
        self.keep_alive_task: Optional[asyncio.Task] = None

    async def send_data(self, data: Dict[str, Any]) -> None:
        await self.websocket.send_json(data)
        logger.debug(f"Sent to {self.username}: {data}")

    async def receive_data(self) -> Dict[str, Any]:
        data: Dict[str, Any] = await self.websocket.receive_json()
        logger.debug(f"Received from {self.username}: {data}")
        return data

    async def start_keep_alive(self, interval: int = 20) -> None:
        async def ping() -> None:
            try:
                while True:
                    await self.websocket.send_json({"type": "ping"})
                    await asyncio.sleep(interval)
            except Exception:
                logger.info(f"Player {self.username} disconnected")

        self.keep_alive_task = asyncio.create_task(ping())
        
    def to_json(self):
        return {"username": self.username, "score": self.score, "place": self.place}


class House:
    def __init__(self, host: Host, players: List[Player], config: TournamentConfig) -> None:
        self.host: Optional[Host] = host
        self.players: List[Player] = players
        self.time_per_question: int = config.time_per_question
        self.answer: int = 0
        logger.info(f"Created house")

    def assign_player_places(self) -> None:
        sorted_players: List[Player] = sorted(self.players, key=lambda p: p.score, reverse=True)
        for i, player in enumerate(sorted_players):
            player.place = i + 1

    def generate_equation(self) -> Tuple[str, int]:
        equation, answer = generate_arithmetic(difficulty="medium")
        self.answer = answer
        return equation, answer

    async def collect_powerups(self) -> Dict[Player, Dict[str, Any]]:
        logger.info(f"Collecting powerups from {len(self.players)} players")

        tasks: Dict[Player, asyncio.Task] = {player: asyncio.create_task(player.receive_data()) for player in self.players}
        done, _ = await asyncio.wait(tasks.values(), timeout=5)

        powerups: Dict[Player, Dict[str, Any]] = {}
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

    async def collect_answers(self) -> Dict[Player, Optional[Dict[str, Any]]]:
        logger.info(f"Collecting answers from {len(self.players)} players")

        tasks: Dict[asyncio.Task, Player] = {
            asyncio.create_task(player.receive_data()): player
            for player in self.players
        }
        answers: Dict[Player, Optional[Dict[str, Any]]] = {}

        start_time = asyncio.get_event_loop().time()

        try:
            for completed in asyncio.as_completed(tasks.keys(), timeout=self.time_per_question):
                try:
                    result = await completed
                    player = next(p for p in self.players if p.username == result["username"])
                    answers[player] = result
                    

                    logger.info(f"Player {player.username} submitted answer: {result}")
                    if self.host:
                        await self.host.send_data({
                            "state": "ui_update",
                            "player": player.to_json(),
                            "update": "player_answered",
                        })
                except Exception as e:
                    logger.exception(f"Error handling answer for task {completed}:")
        except asyncio.TimeoutError:
            logger.warning("Timed out waiting for player answers.")

        for task, player in tasks.items():
            if player not in answers:
                task.cancel()
                answers[player] = None
                logger.warning(f"Player {player.username} did not answer in time")

        end_time = asyncio.get_event_loop().time()
        logger.info(f"Collected answers in {end_time - start_time:.2f}s: {answers}")
        return answers


    async def start_match(self, round_count: int) -> Player:
        logger.info(f"Starting match for {round_count} rounds")

        current_status: str = "waiting_for_round_start"
        round_index: int = 0

        while current_status != "game_ended":
            if current_status == "waiting_for_round_start":
                current_status = await self.handle_round_start()
            elif current_status == "waiting_for_host":
                current_status = await self.handle_host_phase(round_index, round_count)
                round_index += 1

        winner: Player = max(self.players, key=lambda p: p.score)
        return winner
    
    async def broadcast(self, state: Optional[str] = None, **extra: Any) -> None:
        data: Dict[str, Any] = {"state": state, **extra} if state else extra
        await asyncio.gather(*(p.send_data(data) for p in self.players), return_exceptions=True)

    async def handle_round_start(self) -> str:
        equation, answer = self.generate_equation()
        logger.info(f"Equation: {equation}, Answer: {answer}")

        if self.host:
            await self.host.send_data({"state": "prep_round", "equation": equation})

        await self.broadcast("prep_round")
        return "waiting_for_host"

    async def handle_host_phase(self, round_index: int, total_rounds: int) -> str:
        host_data: Dict[str, Any] = {}
        try:
            while host_data.get("state") != "started_round":
                host_data = await self.host.websocket.receive_json()
                logger.info(f"Received data from host: {host_data}")
        except Exception as e:
            logger.warning(f"Host disconnected unexpectedly: {e}")
            return "game_ended"

        logger.info(f"Received host data: {host_data}")

        await self.broadcast("round_ongoing", answer=self.answer)
        await self.host.send_data({"state": "round_ongoing", "current_round": round_index})

        round_results = await self.collect_answers()
        self.assign_scores(round_results, self.answer)
        self.assign_player_places()

        logger.info("Round ended")

        if round_index < total_rounds - 1:
            await self.round_end_phase()
            return "waiting_for_round_start"
        else:
            await self.end_game()
            return "game_ended"

    async def round_end_phase(self) -> None:
        await self.broadcast_round_data()
        if self.host:
            await self.host.send_data({"state": "round_ended", "players": [p.to_json() for p in self.players]})
        await asyncio.sleep(5)

    async def broadcast_round_data(self) -> None:
        await asyncio.gather(*(p.send_data({"state": "round_ended", "score": p.score, "place": p.place}) for p in self.players))

    async def end_game(self) -> None:
        await self.broadcast("game_over", **{p.username: p.score for p in self.players})
        if self.host:
            await self.host.send_data({"state": "game_over", "players": [p.to_json() for p in self.players]})

    def assign_scores(self, round_results: Dict[Player, Optional[Dict[str, Any]]], answer: int) -> Dict[str, int]:
        scores: Dict[str, int] = {}
        for player, data in round_results.items():
            logger.info(f"Player {player.username} Data {data}")
            try:
                if data is not None and int(data.get("answer")) == answer:
                    player.is_correct = True
                    min_score: int = 100
                    max_score: int = 500
                    t: float = data.get("time_took", 0) / self.time_per_question
                    score: int = round(min_score + (max_score - min_score) * (1 - t) ** 2)
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


class Host:
    def __init__(self, lobby_id: str, websocket: WebSocket) -> None:
        self.lobby_id: str = lobby_id
        self.websocket: WebSocket = websocket

    async def send_data(self, data: Dict[str, Any]) -> None:
        await self.websocket.send_json(data)
        logger.debug(f"Sent to host: {data}")


lobby_manager: LobbyManager = LobbyManager()

@app.get("/host")
async def get() -> str:
    id: str = lobby_manager.generate_id()
    logger.info(f"Host tournament request")
    lobby_manager.tournaments[id] = Tournament(id)
    return id


@app.websocket("/ws/{lobby_id}")
async def player_websocket_endpoint(websocket: WebSocket, lobby_id: str) -> None:
    await websocket.accept()
    tournament: Optional[Tournament] = lobby_manager.tournaments.get(lobby_id)
    if tournament:
        username: str = (await websocket.receive_json())["username"]
        player = Player(websocket, username)
        logger.info(f"Player {username} connected to lobby {lobby_id}")
        await player.start_keep_alive(KEEP_ALIVE_INTERVAL)

        tournament.players.append(player)
        players: List = [p.to_json() for p in tournament.players]
        if tournament.host:
            await tournament.host.send_data({"state": "waiting_for_start", "players": players})
        await websocket.send_json({"state": "prep_game"})

        try:
            while True:
                await asyncio.sleep(IDLE_TIMEOUT)
        except Exception:
            logger.info(f"Player {username} disconnected")
        finally:
            if player in tournament.players:
                tournament.players.remove(player)
            if player.keep_alive_task:
                player.keep_alive_task.cancel()
    else:
        await websocket.close()


@app.websocket("/ws/host/{lobby_id}")
async def host_websocket_endpoint(websocket: WebSocket, lobby_id: str) -> None:
    await websocket.accept()
    logger.info(f"Host connected to lobby {lobby_id}")
    tournament: Optional[Tournament] = lobby_manager.tournaments.get(lobby_id)
    if tournament:
        tournament.host = Host(lobby_id, websocket)
        while True:
            data: Dict[str, Any] = await websocket.receive_json()
            if data["state"] == "start_game":
                await tournament.start_tournament()
                break
        try:
            while True:
                await asyncio.sleep(IDLE_TIMEOUT)
        except Exception as e:
            logger.info(f"Host disconnected: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
