from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


DATABASE_URL = "sqlite:///./subscriptions.db"


class Base(DeclarativeBase):
    """класс для всех ORM-моделей."""


engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

