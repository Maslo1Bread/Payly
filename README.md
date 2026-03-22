# Решение для отслеживания подписок

### Решение для отслеживания активных подписок. Добавлять можно как в ручную, так и с помощью почты.


***


## Поддерживаемые приложения

- **SoundCloud** 
- **Discord**
- **Telegram**
- **Yandex Plus**
- **Boosty** *(без уточнения автора)*
- **YouTube**
- **Spotify**
- **Kinopoisk**
- **IVI**
- **Wink**
- **VK Music**
- **KION**


Можно добавить свой сервис через supported_services.json, указав сервис в соответственный массив. Также приложение поддерживает ручной ввод подписок.


***


## Установка и запуск

### Backend

1. **Запуск PowerShell №1**

2. `cd pathToFolder\Payly`

3. `python -m venv .venv`

4. `.\.venv\Scripts\Activate.ps1`

5. `pip install -r requirements.txt`

6. ```bash
   $env:GMAIL_CLIENT_ID="ВАШ_ТОКЕН"
   $env:GMAIL_CLIENT_SECRET="ВАШ_ТОКЕН"
   ```

   1. Видео-инструкция по получению токенов [тык](https://youtu.be/V5tav-El5GI)

   2. Для тестирования приложения, рекомендую вставлять следующие URl
   ```http://127.0.0.1:8001
    http://127.0.0.1:8000/integrations/gmail/oauth/callback
    http://127.0.0.1:8000/integrations/gmail/oauth/callback/
    http://127.0.0.1:8000
    ```
- Видео-инструкция по получению токенов [тык](https://youtu.be/V5tav-El5GI)

7. `uvicorn backend.main:app --reload`

 - API будет на `http://127.0.0.1:8000`
 - Swagger: `http://127.0.0.1:8000/docs`


### Frontend

1. **Запуск PowerShell №2**

2. `cd pathToFolder\Payly\frontend`

3. `python -m http.server 8001`

 - Сайт будет на `http://127.0.0.1:8001`


__***Все вышеуказанное было сделано и протестированно в PowerShell 7***__


***


### Зависимости

- **fastapi**
- **uvicorn**
- **SQLAlchemy**
- **pydantic**
- **email-validator**
- **cryptography**
- **requests**
- **google-auth-oauthlib**
- **google-api-python-client**


### Структура проекта

- **backend/**
  - auth.py
  - crud.py
  - database.py
  - email_keyword_parser.py
  - email_providers.py
  - fernet_utils.py
  - main.py
  - models.py
  - provider_token_store.py
  - schemas.py
  - token_store.py
  - token_store.py
  - supported_services.json
  - routers/auth.py
  - routers/subscriptions.py
  - routers/integrations.py


- **frontend/**
  - auth.html
  - content.html
  - index.html
  - registration.html
  - payly.js
  - style.css




