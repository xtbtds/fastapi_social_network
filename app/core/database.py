from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings


SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# an instance of the SessionLocal will be database session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# inherit from this class to create each of the database models or classes (the ORM models)
Base = declarative_base()