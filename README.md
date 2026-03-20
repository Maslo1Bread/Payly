## Решение для отслеживания подписок

Решение для отслеживания активных подписок. Добавлять можно как в ручную, так и с помощью почты.

### Поддерживаемые приложения

- **SoundCloud**
- **Discord**
- **Telegram**
- **Yandex Plus**
- **Boosty** (не уверен если честно :p)

### Стек

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
  - **main.py**
  - **database.py**
  - **models.py**
  - **schemas.py**
  - **crud.py**
  - **auth.py**
  - **token_store.py**
  - **routers/auth.py**
  - **routers/subscriptions.py**
  - **email_keyword_parser.py**
  - **email_providers.py**
  - **fernet_utils.py**
  - **provider_token_store.py**
  - **token_store.py**

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

5. Для корректной работы подстановки из gmail нужны токены client_id и client_id_secret. Получить их вы можете здесь https://console.cloud.google.com/. **ОБЯЗАТЕЛЬНО** должен быть включен GMAIL API. Для теста можно добавить себя в разрешенные пользователи, либо включить публичную версию. OAuth2 будет работать на URi которые вы указали присоздании приложения в google. Для тестов рекомендую вписывать эти:

- `http://127.0.0.1:8001`
- `http://127.0.0.1:8000/integrations/gmail/oauth/callback`
- `http://127.0.0.1:8000/integrations/gmail/oauth/callback/`
- `http://127.0.0.1:8000`

В shell вставляете токены в формате:
   ```bash
   $env:GMAIL_CLIENT_ID="ВАШ_ТОКЕН"
   $env:GMAIL_CLIENT_SECRET="ВАШ_ТОКЕН"
   ```

- Видео-инструкция по получению токенов [тык]([https://youtu.be/NtBX97OfnqU](https://youtu.be/V5tav-El5GI))


6. `uvicorn backend.main:app --reload`

 - API будет на `http://127.0.0.1:8000`
 - Swagger: `http://127.0.0.1:8000/docs`


#### Frontend

1. **Запуск PowerShell №2**

2. `cd pathToFolder\Payly\frontend`

3. `python -m http.server 8001`

 - Сайт будет на `http://127.0.0.1:8001`




