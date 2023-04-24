from sqlalchemy.orm import Session

from app import models, schemas
from app.utils import pass_hash


def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()


def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = pass_hash.get_hashed_password(user.password)
    db_user = models.User(
        email=user.email,
        hashed_password=hashed_password,
        name=user.name,
        surname=user.surname,
        is_active=False,
    )
    db.add(db_user)
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
