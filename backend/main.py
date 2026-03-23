"""
Простой backend-сервер для учебного проекта по отслеживанию подписок.

Стек:
- FastAPI
- SQLite
- SQLAlchemy ORM
- Pydantic

Структура проекта:
backend/
  main.py
  database.py
  models.py
  schemas.py
  crud.py
  auth.py
  routers/auth.py
  routers/subscriptions.py

=====================================
ИНСТРУКЦИЯ ПО ЗАПУСКУ (Windows/PowerShell)
=====================================
1. Перейдите в корень проекта:
   cd D:\\DifferentScripts\\Payly

2. (Рекомендуется) создайте и активируйте виртуальное окружение:
   python -m venv .venv
   .\\.venv\\Scripts\\Activate.ps1

3. Установите зависимости:
   pip install -r requirements.txt

4. Запустите сервер разработки:
   uvicorn backend.main:app --reload

5. Откройте документацию Swagger:
   http://127.0.0.1:8000/docs

Основные эндпоинты:
- POST /register — регистрация
- POST /login — логин, возвращает Bearer-токен
- GET /subscriptions — список подписок текущего пользователя
- POST /subscriptions — создание подписки
- PUT /subscriptions/{id} — обновление подписки
- DELETE /subscriptions/{id} — удаление подписки
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models
from .database import engine
from .routers import auth as auth_router
from .routers import subscriptions as subscriptions_router
from .routers import integrations as integrations_router


# Создаём таблицы в БД (если их ещё нет)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Subscriptions Tracker API")

# Простая настройка CORS для удобства разработки (при необходимости можно сузить список доменов)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
app.include_router(auth_router.router)
app.include_router(subscriptions_router.router)
app.include_router(integrations_router.router)


@app.get("/", tags=["root"])
def read_root():
    """
    Простой корневой эндпоинт, чтобы убедиться, что сервер запущен.
    """
    return {"message": "Subscriptions Tracker API is running"}

