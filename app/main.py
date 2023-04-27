import logging
from datetime import datetime, timedelta
from typing import List

import jose
from fastapi.responses import HTMLResponse, JSONResponse, ORJSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from typing_extensions import Annotated

from app import crud, models, schemas
from app.core.config import settings
from app.core.database import SessionLocal
from app.schemas import User
from app.utils import auth, pass_hash
from email_core.celery_worker import task_send_notification
from email_core.emails import send_confirmation
from fastapi import (BackgroundTasks, Depends, FastAPI, HTTPException, Request,
                     Response, status)

app = FastAPI()


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except:
        db.rollback()
    finally:
        db.close()


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


templates = Jinja2Templates(directory="templates")


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
    


@app.get("/users/", response_model=List[schemas.User])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users


@app.get("/users/{user_id}", response_model=schemas.User)
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@app.post("/users/{user_id}/posts/", response_model=schemas.Post)
def create_post_for_user(
    user_id: int, post: schemas.PostCreate, db: Session = Depends(get_db)
):
    return crud.create_user_post(db=db, post=post, user_id=user_id)


@app.get("/users/{user_id}/posts/", response_model=List[schemas.Post])
def read_user_posts(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    posts = crud.get_user_posts(db, user_id=db_user.id)
    return posts


@app.get("/posts/", response_model=List[schemas.Post])
def read_posts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    posts = crud.get_posts(db, skip=skip, limit=limit)
    return posts


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# Dependency
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], db: Session = Depends(get_db)
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("email")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception
    user = crud.get_user_by_email(db, email=token_data.email)
    if user is None:
        raise credentials_exception
    return user


# Dependency
async def get_current_active_user(
    current_user: Annotated[schemas.User, Depends(get_current_user)]
):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# Login endpoint
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
    return {"access_token": access_token, "refresh_token": refresh_token}
    # 1. should be store in cookies
    # 2. should become invalid when new pair is created



@app.post("/refresh")
async def refresh(refresh_token: str, db: Session = Depends(get_db)):
    user = auth.verify_token(db, refresh_token)
    print('-----------------------------')
    print(user)
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



# Endpoint get current user
@app.get("/users/me/", response_model=schemas.User)
async def read_users_me(
    current_user: Annotated[schemas.User, Depends(get_current_active_user)]
):
    return current_user


# Dependency
async def get_current_admin_user(
    current_user: Annotated[schemas.User, Depends(get_current_active_user)]
):
    if not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only admins have access to this.")
    return current_user



@app.get("/maintenance")
async def set_maintenance_mode(
    current_admin_user: Annotated[schemas.User, Depends(get_current_admin_user)],
    db: Session = Depends(get_db)
):
    users = crud.get_all_users(db)
    emails = [user.email for user in users]
    task_send_notification.delay(emails)
    return 'ok'

# @app.post("/ex1")
# def run_task(data=Body(...)):
#     amount = int(data["amount"])
#     x = data["x"]
#     y = data["y"]
#     task1 = create_task.delay(amount, x, y)
#     task2 = create_task.delay(amount, x, y)
#     task3 = create_task.delay(amount, x, y)
#     return JSONResponse({"Result1": task1.get(), "Result2": task2.get(), "Result3": task3.get()})

