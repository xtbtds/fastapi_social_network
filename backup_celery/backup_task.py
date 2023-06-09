from backup_celery.celery import app
from app.redis_depend import get_redis_pool
from app.dependencies import get_db
import asyncio
from datetime import datetime
from app import crud, schemas

async def backup():
    pool = await get_redis_pool()
    db = next(get_db())
    try:
        chats = await pool.keys("stream:*")
        redis_messages = []
        for chat in chats:
            last_backuped = crud.last_message_date_in_chat(db, chat_id=int(chat.split(":")[-1]))
            chat_messages = await pool.xrange(
                stream = chat,
                start = '-',
                stop = '+'
            )
            for message in chat_messages:
                message_date_time = datetime.strptime(message[1]['date_time'], "%Y-%m-%dT%H:%M:%S.%f")
                if not last_backuped or message_date_time > last_backuped.date_time:
                    message_dict = {
                                'redis_id': message[0], 
                                'content': message[1]['content'],
                                'date_time': message[1]['date_time'],
                                'owner_id': message[1]['user_id'],
                                'chat_id': message[1]['chat_id']
                                }
                    message_model = schemas.Message(**message_dict)
                    redis_messages.append(message_model)
            print(f'im checking your messages in chat {chat.split(":")[-1]}...')
        if redis_messages:
            print(f'Backup of {len(redis_messages)} messages started')
            result = crud.create_message(db, redis_messages)
        else:
            print('Nothing to backup.')
    finally:
        pool.close()
        db.close()

@app.task
def check():
    return asyncio.run(backup())
