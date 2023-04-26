import asyncio
import logging

from celery import Celery

from app.core.config import settings
from email_core.emails import send_notification

celery=Celery(__name__)
celery.conf.broker_url=settings.CELERY_BROKER_URL
celery.conf.result_backend=settings.CELERY_RESULT_BACKEND

@celery.task(name="task_send_notification")
def task_send_notification(email):
    logging.info("inside sync task function")
    return asyncio.run(send_notification(email=email))


# @celery.task(name="create_task")
# def create_task(a, b, c):
#     time.sleep(a)
#     return b + c