import asyncio
import logging
import time
import pytz
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import List

import aioredis
import jose
from aioredis.errors import \
    ConnectionClosedError as ServerConnectionClosedError
from fastapi.responses import HTMLResponse, JSONResponse, ORJSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi.websockets import WebSocket, WebSocketDisconnect
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketDisconnect
from typing_extensions import Annotated
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from app import crud, models, schemas
from app.core.config import settings
from app.dependencies import (get_current_active_user, get_current_admin_user,
                              get_current_user, get_db)
from app.routers import users
from app.schemas import User
from app.utils import auth, pass_hash
from backup_celery.maintenance_task import task_send_notification
from email_core.emails import send_confirmation
from fastapi import (BackgroundTasks, Depends, FastAPI, HTTPException, Request,
                     Response, status)

app = FastAPI()
app.include_router(users.router)
templates = Jinja2Templates(directory="templates")


@app.post("/register/")
async def create_user(background_tasks: BackgroundTasks, user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )
    db_user = crud.create_user(db=db, user=user)
    if db_user:
        background_tasks.add_task(send_confirmation, user.email, db_user)
        return ORJSONResponse(User(**db_user.__dict__).dict(),status.HTTP_201_CREATED)
    return Response(status_code=status.HTTP_403_FORBIDDEN)


@app.get("/verification", response_class=HTMLResponse)
def email_verification(token: str, db: Session = Depends(get_db)):
    try:
        user = auth.verify_token(db, token)
    except jose.exceptions.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user and not user.is_active:
        user.is_active = True
        db.add(user)
        db.commit()
        return 'ok'
    elif user.is_active:
        return 'user has been activated already'
    

@app.get("/posts/", response_model=List[schemas.Post])
def read_posts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    posts = crud.get_posts(db, skip=skip, limit=limit)
    return posts


@app.post("/login")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Session = Depends(get_db),
):
    user = crud.get_user_by_email(db, form_data.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with provided email doesn't exist. You need to register first",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="You need to activate your account before logging in. Check your email.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not pass_hash.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=int(settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    access_token = auth.create_access_token(
        data={"email": user.email}, expires_delta=access_token_expires
    )
    refresh_token_expires = timedelta(minutes=int(settings.REFRESH_TOKEN_EXPIRE_MINUTES))
    refresh_token = auth.create_refresh_token(
        data={"email": user.email}, expires_delta=refresh_token_expires
    )
    # response = JSONResponse(
    #     content={
    #         "access_token": access_token,
    #         "token_type": "bearer",
    #         "token_expiry": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    #     }
    # )
    # response.set_cookie(
    #     key="invoice_processing",
    #     value=refreshTokenId,
    #     expires=cookie_token_expiration_in_ms,
    #     httponly=True,
    # )
    return {"access_token": access_token, "refresh_token": refresh_token}
    # 1. should be store in cookies
    # 2. should become invalid when new pair is created


@app.post("/refresh")
async def refresh(refresh_token: str, db: Session = Depends(get_db)):
    user = auth.verify_token(db, refresh_token)
    access_token_expires = timedelta(minutes=int(settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    access_token = auth.create_access_token(
        data={"email": user.email}, expires_delta=access_token_expires
    )
    refresh_token_expires = timedelta(minutes=int(settings.REFRESH_TOKEN_EXPIRE_MINUTES))
    refresh_token = auth.create_refresh_token(
        data={"email": user.email}, expires_delta=refresh_token_expires
    )
    return {"access_token": access_token, "refresh_token": refresh_token}
    # 1. should be store in cookies
    # 2. should become invalid when used (delete cookie or what?)
    # 3. question: when verifying token, should its expiration date be checked?


@app.get("/maintenance")
async def set_maintenance_mode(
    current_admin_user: Annotated[schemas.User, Depends(get_current_admin_user)],
    db: Session = Depends(get_db)
):
    users = crud.get_all_users(db)
    emails = [user.email for user in users]
    task_send_notification.delay(emails)
    return 'ok'



async def get_redis_pool():
    return await aioredis.create_redis_pool(('redis', 6379), encoding='utf-8')



@app.post("/chats/add")
async def add_user(
    current_active_user: Annotated[schemas.User, Depends(get_current_active_user)],
                                  chat_id: int, 
                                  user_id: int, 
                                  pool = Depends(get_redis_pool),
                                  db = Depends(get_db)):
    current_user = crud.get_user_by_email(db, current_active_user.email)
    isMemberCurrent = await pool.sismember(f"{chat_id}:users", current_user.id)
    isMemberTarget = await pool.sismember(f"{chat_id}:users", user_id)
    if not isMemberCurrent and user_id != current_user.id:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, 
                        content={'msg':f'User {current_user.id}, you must be a member of the chat in order to add other member'})
    if isMemberTarget:
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, 
                        content={"msg":f"User {user_id} is already a chat member"})
    else:
        await pool.sadd(f"{chat_id}:users", user_id)
        await pool.sadd(f"{user_id}:chats", chat_id)
        stream = f"stream:{chat_id}"
        date_time = datetime.now()
        # date_time = pytz.utc.localize(datetime.utcnow())
        # date_time = date_time_default.astimezone(pytz.timezone("Europe/Warsaw"))
        if current_user.id == user_id:
            await pool.xadd(stream=stream,
                            fields={"chat_id": str(chat_id),
                                    "user_id": str(current_user.id),
                                    "content": f"User {user_id} joined the chat",
                                    "date_time": date_time.isoformat()
                                    },
                            message_id=b'*',
                            max_len=100)
        else:
            await pool.xadd(stream=stream,
                            fields={"chat_id": str(chat_id),
                                    "user_id": str(current_user.id),
                                    "content": f"User {current_user.id} added user {user_id}",
                                    "date_time": date_time.isoformat()
                                    },
                            message_id=b'*',
                            max_len=100)
        return JSONResponse(status_code=status.HTTP_201_CREATED, 
                        content={'msg':f'You added user {user_id} to chat {chat_id}'})


@app.post("/chats/remove") # delete?
async def remove_user(chat_id, user_id, pool = Depends(get_redis_pool)):
    await pool.srem(f"{chat_id}:users", user_id)
    await pool.srem(f"{user_id}:chats", chat_id)
    #fix: check if he IS in chat
    #fix: send for all users in a chat "user ... left chat" and add this message to redis stream
    #or user ... removed user ...



async def receive_from_websocket(websocket, user_id):
    """
    receives json data from client over a WebSocket, 
    adds messages in the associated chat stream
    """
    pool = await get_redis_pool()
    ws_connected = True
    while ws_connected:
        message = await websocket.receive_json()
        if message:
            # fix: user pydantic data validation
            try:
                chat_id = message['chat_id']
                content = message['content']
            except:
                data = {'error': 'invalid data'}
                await websocket.send_json(data)
                continue

            ismember = await pool.sismember(f"{chat_id}:users", user_id)
            if ismember:
                stream = f"stream:{chat_id}"
            else:
                data = {"error": "you can't post to this chat"}
                await websocket.send_json(data)
                continue
        date_time = datetime.now()
        # date_time = pytz.utc.localize(datetime.utcnow())
        # date_time = date_time_default.astimezone(pytz.timezone("Europe/Warsaw"))
        fields = {
                "chat_id": str(chat_id),
                "user_id": str(user_id),
                "content": str(content),
                "date_time": date_time.isoformat()
        }
        await pool.xadd(stream=stream,
                            fields=fields,
                            message_id=b'*',
                            max_len=100)


async def send_to_websocket(websocket: WebSocket, user_id):
    """
    waits for new items in chat stream and
    sends data to client over a WebSocket
    """
    pool = await get_redis_pool()
    chats = await pool.smembers(f"{user_id}:chats")
    logging.warn(chats)
    if chats:
        streams = [f"stream:{chat_id}" for chat_id in chats]
        streams_ids_dict = OrderedDict.fromkeys(streams, b"0-0")
        latest_ids = streams_ids_dict.values()
        ws_connected = True
        first_run = False
        while pool and ws_connected:
            try:
                if first_run:
                    pass
                    # fetch some previous chat history
                    # for stream in streams:
                    #     print(stream, '-----------')
                    #     messages = await pool.xrevrange(
                    #         stream=stream,
                    #         count=0,
                    #         start='+',
                    #         stop='-'
                    #     )
                    #     print(messages)
                    #     first_run = False
                    #     messages.reverse()
                    #     for message_id, data in messages:
                    #         data['message_id'] = message_id
                    #         await websocket.send_json(data)
                else:
                    messages = await pool.xread(
                    streams=streams,
                    count=3,
                    timeout=0, 
                    latest_ids=list(latest_ids)
                    )
                    for stream_id, message_id, data in messages:
                        data['message_id'] = message_id
                        await websocket.send_json(data)
                        streams_ids_dict[f"stream:{data['chat_id']}"] = message_id
                        latest_ids = streams_ids_dict.values()

            except ConnectionClosedError:
                ws_connected = False

            except ConnectionClosedOK:
                ws_connected = False

            except WebSocketDisconnect:
                ws_connected = False

            except ServerConnectionClosedError:
                print('redis server connection closed')
                return
    pool.close()



@app.websocket("/chats")
async def websocket(websocket: WebSocket, token, db=Depends(get_db)):
    await websocket.accept()
    try:
        decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=settings.ALGORITHM)
        email = decoded_token.get('email')
        user = crud.get_user_by_email(db, email)
    except jose.exceptions.ExpiredSignatureError:
        await websocket.send_json({"error": f"Your session has expired, log in again"})
        await websocket.close()
        return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED)
    except:
        await websocket.send_json({"error": f"Not authenticated"})
        await websocket.close()
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST)
    await asyncio.gather(receive_from_websocket(websocket, user_id=user.id),
                            send_to_websocket(websocket, user_id=user.id))
