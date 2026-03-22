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

# настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(subscriptions_router.router)
app.include_router(integrations_router.router)


@app.get("/", tags=["root"])
def read_root():
    return {"message": "Subscriptions Tracker API is running"}

