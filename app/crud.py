from sqlalchemy.orm import Session

from app import models, schemas
from app.utils import pass_hash
from typing import List
from sqlalchemy import desc


def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()

def get_all_users(db: Session):
    return db.query(models.User).all()


def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = pass_hash.get_hashed_password(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        name=user.name,
        surname=user.surname,
        is_active=False,
        is_admin=False
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def get_posts(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Post).offset(skip).limit(limit).all()


def get_user_posts(db: Session, user_id: int):
    posts = db.query(models.Post).filter(models.Post.owner_id == user_id).all()
    return posts


def create_user_post(db: Session, post: schemas.PostCreate, user_id: int):
    db_item = models.Post(**post.dict(), owner_id=user_id)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


def get_user_chats(db: Session, user_id: int):
    chats_models = db.query(models.UserChat).filter(models.UserChat.user_id == user_id).all()
    chats_ids = [chat.chat_id for chat in chats_models]
    return chats_ids


def create_message(db: Session, messages: List[schemas.Message]):
    for m in messages:
        db_message = models.Message(
            **m.dict()
        )
        db.add(db_message)
        db.commit()
        db.refresh(db_message)
    return 'ok'

def last_message_date_in_chat(db: Session, chat_id: int):
    row = db.query(models.Message).filter(models.Message.chat_id == chat_id).order_by(desc(models.Message.date_time)).first()
    return row
