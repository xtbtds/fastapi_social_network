from typing import List, Union

from pydantic import BaseModel, Field
from datetime import datetime

# POST
class PostBase(BaseModel):
    title: str
    content: Union[str, None] = None

class PostCreate(PostBase):
    pass

class Post(PostBase):
    id: int
    owner_id: int

    class Config:
        orm_mode = True


# USER
class UserBase(BaseModel):
    email: str

class UserDetailed(UserBase):
    name: str
    surname: str

class UserCreate(UserDetailed):
    password: str

class User(UserBase):
    is_active: bool
    is_admin: bool
    class Config:
        orm_mode = True


# MESSAGE
class Message(BaseModel):
    redis_id: str
    context: str
    datetime: datetime
    owner_id: int
    chat_id: int
    class Config:
        orm_mode = True


# TOKEN
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Union[str, None] = None