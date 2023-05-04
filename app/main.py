from datetime import datetime, timedelta
from typing import List
import time
import jose
from fastapi.responses import HTMLResponse, JSONResponse, ORJSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi.websockets import WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing_extensions import Annotated
from fastapi.websockets import WebSocket, WebSocketDisconnect
import asyncio
import logging
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK
from aioredis.errors import ConnectionClosedError as ServerConnectionClosedError
from app import crud, schemas, models
from app.core.config import settings
from app.dependencies import (get_current_active_user, get_current_admin_user,
                              get_current_user, get_db)
from app.routers import users
from app.schemas import User
from app.utils import auth, pass_hash
from email_core.celery_worker import task_send_notification
from email_core.emails import send_confirmation
from fastapi import (BackgroundTasks, Depends, FastAPI, HTTPException, Request,
                     Response, status)
import aioredis

app = FastAPI()
app.include_router(users.router)


async def get_redis_pool():
    pool = await aioredis.create_redis_pool(('redis', 6379), encoding='utf-8')
    return pool


async def receive_from_websocket(redis_conn, websocket, stream):
    ws_connected = True
    pool = await get_redis_pool()
    while ws_connected:
        message = await websocket.receive_text()
        result = await redis_conn.xadd(stream, {"data": message})


async def read_from_stream(stream, websocket: WebSocket):
    pool = await get_redis_pool()
    latest_ids = [b'0-0']
    ws_connected = True
    first_run = True
    while pool and ws_connected:
        try:
            # if first_run:
            #     # fetch some previous chat history
            #     events = await pool.xrevrange(
            #         stream=stream,
            #         count=5,
            #         start='+',
            #         stop='-'
            #     )
            #     first_run = False
            #     events.reverse()
            #     for e_id, e in events:
            #         e['e_id'] = e_id
            #         await websocket.send_json(e)
            # else:
            messages = await pool.xread(
                streams=[stream],
                count=3,
                timeout=0,
                latest_ids=latest_ids
            )
            for stream_id, message_id, data in messages:
                data['message_id'] = message_id
                await websocket.send_json(data)
                # print(data)
                logging.warning(data)
                latest_ids = [message_id]
        except ConnectionClosedError:
            ws_connected = False

        except ConnectionClosedOK:
            ws_connected = False

        except ServerConnectionClosedError:
            print('redis server connection closed')
            return
    pool.close()




def get_user_chats(db: Session, user_id: int):
    chats_ids = db.query(models.UserChat).filter(models.UserChat.user_id == user_id).all()
    chats_names = [db.query(models.Chat).filter(models.Chat.id == chat.id).all() for chat in chats_ids]
    return chats_names


@app.websocket("/chats/{room_id}")
async def websocket(websocket: WebSocket, room_id, db=Depends(get_db)):
    stream = f"stream:{room_id}"
    print('in an endpoint')
    await websocket.accept()
    # await receive_from_websocket(redis_conn, websocket, stream) #WORKS
    await read_from_stream(stream, websocket=websocket)
