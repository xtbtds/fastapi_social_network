import asyncio
import logging
import aioredis
from aioredis.client import PubSub, Redis
from fastapi import FastAPI, Request
from fastapi.websockets import WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from typing import List
from fastapi.templating import Jinja2Templates

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
app = FastAPI()


templates = Jinja2Templates(directory="templates")


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()

@app.get("/chat")
async def get(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})


@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    await manager.broadcast(f"Client #{client_id} joined the chat")
    await redis_connector(websocket, client_id)



async def consumer_handler(conn: Redis, ws: WebSocket, client_id):
    try:
        while True:
            message = await ws.receive_text()
            if message:
                await conn.publish("chat:c", message)
    except WebSocketDisconnect as exc:
        manager.disconnect(ws)
        await manager.broadcast(f"Client #{client_id} left the chat")


async def producer_handler(pubsub: PubSub, ws: WebSocket, client_id):
    await pubsub.subscribe("chat:c")
    try:
        while True:
            message = await pubsub.get_message(ignore_subscribe_messages=True)
            if message:
                await manager.send_personal_message(message.get('data'), ws)
    except WebSocketDisconnect as exc:
        manager.disconnect(ws)
        await manager.broadcast(f"Client #{client_id} left the chat")


async def redis_connector(websocket: WebSocket, client_id):
    redis_conn = await get_redis_pool()
    pubsub = redis_conn.pubsub()
    consumer_task = consumer_handler(conn=redis_conn, ws=websocket, client_id=client_id)
    producer_task = producer_handler(pubsub=pubsub, ws=websocket, client_id=client_id)
    done, pending = await asyncio.wait(
        [consumer_task, producer_task], return_when=asyncio.FIRST_COMPLETED,
    )
    logger.debug(f"Done task: {done}")
    for task in pending:
        logger.debug(f"Canceling task: {task}")
        task.cancel()


async def get_redis_pool():
    return await aioredis.from_url(f'redis://redis:6379', encoding="utf-8", decode_responses=True)