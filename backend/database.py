from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase


# SQLite URL. Файл БД будет создан в корне проекта.
DATABASE_URL = "sqlite:///./subscriptions.db"


class Base(DeclarativeBase):
    """Базовый класс для всех ORM-моделей."""


# Параметр check_same_thread обязателен для использования SQLite с многопоточным сервером
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Фабрика сессий для работы с БД
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Зависимость FastAPI для получения сессии БД.
    Используется в эндпоинтах через Depends.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

