from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    surname = Column(String)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    is_active = Column(Boolean, default=False, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    # role_id = Column(Integer, ForeignKey("roles.id"))

    posts = relationship("Post", back_populates="owner")
    # role = relationship("Role", back_populates="users")


# class Role(Base):
#     __tablename__ = "roles"
#     id = Column(Integer, primary_key=True, index=True)
#     name = Column(String)
#     description = Column(Text)

#     users = relationship("User", back_populates="role")



class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    content = Column(String)
    owner_id = Column(Integer, ForeignKey("users.id"))

    owner = relationship("User", back_populates="posts")


# class Group(Base):
#     __tablename__ = "groups"
#     id = Column(Integer, primary_key=True, index=True)
#     name = Column(String)
