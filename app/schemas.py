from typing import List, Union

from pydantic import BaseModel, Field
from datetime import datetime

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
        # orm_mode will tell the Pydantic model to read the data even if it is not a dict,
        # but an ORM model (or any other arbitrary object with attributes).

        # Without orm_mode: it wouldn't include the relationship data.
        # With orm_mode: Pydantic will try to access the data from attributes (instead of assuming a dict)


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


class Message(BaseModel):
    redis_id: str
    context: str
    datetime: datetime
    owner_id: int
    chat_id: int
    class Config:
        orm_mode = True

