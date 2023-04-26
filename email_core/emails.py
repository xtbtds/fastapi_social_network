from typing import List

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema
from jose import jwt

from app import schemas
from app.core.config import settings
from app.utils import auth

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

async def send_confirmation(email: List, instance: schemas.User):
    token_data = {"id": instance.id, "email": instance.email}
    token = jwt.encode(token_data, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    template = f"""
        <!DOCTYPE html>
        <html>
            <head>
                <meta charset="utf-8">
            </head>
            <body>
                <div style=" display: flex; align-items: center; justify-content: center; flex-direction: column;">
                    <h3> Account Verification </h3>
                    <br>
                    <p>Please click on the link below to verify your account</p> 
                    <a style="margin-top:1rem; padding: 1rem; border-radius: 0.5rem; font-size: 1rem; text-decoration: none; background: #0275d8; color: white;"
                    href="http://localhost:8080/verification/?token={token}">
                        Verify your email
                    <a>
                </div>
            </body>
        </html>
    """
    message = MessageSchema(
        subject="Account Verification Mail",
        recipients=[email],  # List of recipients, as many as you can pass
        body=template,
        subtype="html",
    )

    fm = FastMail(conf)
    await fm.send_message(message)




# send emails when maintenance mode on
async def send_notification(email):
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
    await fm.send_message(message)
