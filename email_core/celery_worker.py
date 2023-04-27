import asyncio
import logging

from celery import Celery
from app import crud

from app.core.config import settings
from email_core.emails import send_notification

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


# @celery.task(name="create_task")
# def create_task(a, b, c):
#     time.sleep(a)
#     return b + c