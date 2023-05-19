from backup_celery.celery import app
from app.redis_depend import get_redis_pool
from app.dependencies import get_db
import asyncio
from app import crud, schemas

async def backup():
    pool = await get_redis_pool()
    db = next(get_db())
    try:
        chats = await pool.keys("stream:*")
        redis_messages = []
        for chat in chats:
            chat_messages = await pool.xrange(
                stream = chat,
                start = '-',
                stop = '+'
            )
            for message in chat_messages:
                message_dict = {
                            'redis_id': message[0], 
                            'context': message[1]['content'],
                            'datetime': message[1]['date_time'],
                            'owner_id': message[1]['user_id'],
                            'chat_id': message[1]['chat_id']
                            }
                message_model = schemas.Message(**message_dict)
                redis_messages.append(message_model)
        print('im checking your messages', redis_messages)
        result = crud.create_message(db, redis_messages)
        print(result, '====================')
    finally:
        pool.close()
        db.close()


@app.task
def check():
    return asyncio.run(backup())
    # print("I am checking your stuff, ")

