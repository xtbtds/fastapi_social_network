import asyncio
import logging
import os
import time
from typing import List

from celery import Celery
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema
from jose import jwt

from app import schemas
from app.core.config import settings
from app.utils import auth
from email_core.emails import send_notification

celery=Celery(__name__)
celery.conf.broker_url=settings.CELERY_BROKER_URL
celery.conf.result_backend=settings.CELERY_RESULT_BACKEND

conf = ConnectionConfig(
    MAIL_USERNAME=settings.EMAIL_USERNAME,
    MAIL_PASSWORD=settings.EMAIL_PASSWORD,
    MAIL_FROM=settings.EMAIL_USERNAME,
    MAIL_PORT=settings.EMAIL_PORT,
    MAIL_SERVER=settings.EMAIL_SERVER,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
)


@celery.task(name="task_send_notification",ignore_result=True)
async def task_send_notification(email):
    template = """
        <!DOCTYPE html>
        <html>
            <head>
                <meta charset="utf-8">
            </head>
            <body>
                <div style=" display: flex; align-items: center; justify-content: center; flex-direction: column;">
                    <h3> Application unavailable </h3>
                    <br>
                    <p>Application unavailable due to maintenance mode</p> 
                </div>
            </body>
        </html>
    """
    message = MessageSchema(
        subject="Application unavailable due to maintenance mode",
        recipients=[email],  # List of recipients, as many as you can pass
        body=template,
        subtype="html",
    )
    fm = FastMail(conf)
    logging.info(f"==== Before await send_message to {email}")
    print(f"==== Before await send_message to {email}")
    await fm.send_message(message)
