from typing import List, Union

from pydantic import BaseModel


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
    name: str
    surname: str

class UserCreate(UserBase):
    password: str


class User(UserBase):
    id: int
    is_active: bool
    items: List[Post] = []
    class Config:
        orm_mode = True

