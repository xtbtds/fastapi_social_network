import asyncio
import logging
from celery.schedules import crontab
from datetime import datetime
import pytz
import aioredis
from celery import Celery
from app import crud
from fastapi import Depends
from app.core.config import settings
from email_core.emails import send_notification
from app.dependencies import get_db
from app.crud import create_message

celery=Celery(__name__)
celery.conf.broker_url=settings.CELERY_BROKER_URL
celery.conf.result_backend=settings.CELERY_RESULT_BACKEND

async def async_tasks_for_all_users(list_of_emails):
    tasks = []
    for email in list_of_emails:
        task = asyncio.create_task(send_notification(email=email))
        tasks.append(task)
    await asyncio.gather(*tasks)

@celery.task(name="task_send_notification")
def task_send_notification(emails):
    return asyncio.run(async_tasks_for_all_users(list_of_emails=emails))

@celery.task
def check():
    print("I am checking your stuff")



async def get_redis_pool():
    return await aioredis.create_redis_pool(('redis', 6379), encoding='utf-8')


@celery.task(name="backup")
def backup(pool = Depends(get_redis_pool), db = Depends(get_db)):
    date_time_default = pytz.utc.localize(datetime.utcnow())
    date_time = date_time_default.astimezone(pytz.timezone("Europe/Warsaw"))
    chats = pool.keys("stream:*")
    redis_messages = []
    for chat in chats:
        chat_messages = pool.xrange(
            stream = chat,
            start = '-',
            stop = '+'
        )
        redis_messages.append(*chat_messages)
    create_message(db, redis_messages)
    # redis_users_in_chats = {'1': [1,2,3], ...}
    # db.add(redis_messages)
    # db.add(redis_users_in_chats)


# celery.conf.beat_schedule = {
#     'backup-every-six-kours': {
#         'task': 'tasks.backup',
#         'schedule': crontab(), # crontab( minute=0, hour='*/3')
#         # 'args': (16, 16),
#     },
# }

# celery.conf.beat_schedule = {
#     "run-me-every-ten-seconds": {
#         "task": "tasks.check",
#         "schedule": 10.0
#     }
# }

# @celery.on_after_configure.connect
# def setup_periodic_tasks(sender, **kwargs):
#     sender.add_periodic_task(10.0, check, name='add every 10')