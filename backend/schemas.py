from datetime import datetime, date
from typing import Optional, List

from pydantic import BaseModel, EmailStr, Field


# ===== Схемы пользователей =====


class UserBase(BaseModel):
    email: EmailStr = Field(..., description="Email пользователя")


class UserCreate(UserBase):
    password: str = Field(..., min_length=4, description="Пароль (на сервере хранится в виде хэша)")


class UserLogin(UserBase):
    password: str


class UserOut(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ===== Схемы подписок =====


class SubscriptionBase(BaseModel):
    name: str = Field(..., description="Название сервиса")
    price: float = Field(..., ge=0, description="Стоимость подписки")
    billing_cycle: str = Field(..., pattern="^(monthly|yearly)$", description="Периодичность списания")
    next_payment_date: date = Field(..., description="Дата следующего списания")


class SubscriptionCreate(SubscriptionBase):
    pass


class SubscriptionUpdate(BaseModel):
    """
    Обновление подписки — все поля опциональны.
    """

    name: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    billing_cycle: Optional[str] = Field(None, pattern="^(monthly|yearly)$")
    next_payment_date: Optional[date] = None


class SubscriptionOut(SubscriptionBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class SubscriptionsList(BaseModel):
    items: List[SubscriptionOut]


# ===== Схемы для auth токена =====


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

