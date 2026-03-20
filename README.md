## Backend для отслеживания подписок (FastAPI)

Учебный backend-сервер для работы с пользователями и их подписками.

### Стек

- **fastapi**
- **uvicorn**
- **SQLAlchemy**
- **pydantic**
- **email-validator**
- **cryptography**


### Структура проекта

- **backend/**
  - **main.py**
  - **database.py**
  - **models.py**
  - **schemas.py**
  - **crud.py**
  - **auth.py**
  - **token_store.py**
  - **routers/auth.py**
  - **routers/subscriptions.py**

- **frontend/**
  - **auth.html**
  - **content.html**
  - **index.html**
  - **registration.html**
  - **payly.js**
  - **style.css**


### Установка и запуск

#### Backend

1. **Запуск PowerShell №1**

2. `pathToFolder\Payly`

3. `.\.venv\Scripts\Activate.ps1`

4. `pip install -r requirements.txt`

5. `uvicorn backend.main:app --reload`

 - API будет на `http://127.0.0.1:8000`
 - Swagger: `http://127.0.0.1:8000/docs`


#### Frontend

1. **Запуск PowerShell №2**

2. `cd pathToFolder\Payly\frontend`

3. `python -m http.server 8001`

 - Сайт будет на `http://127.0.0.1:8001`


### Основные эндпоинты

- **POST** `/register` — регистрация пользователя
- **POST** `/login` — логин, возвращает Bearer-токен
- **GET** `/subscriptions` — получить подписки текущего пользователя
- **POST** `/subscriptions` — создать подписку
- **PUT** `/subscriptions/{id}` — обновить подписку
- **DELETE** `/subscriptions/{id}` — удалить подписку

Токен из `/login` передаётся в заголовке `Authorization: Bearer <token>`.

