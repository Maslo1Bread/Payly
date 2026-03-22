from datetime import datetime, date

from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, Date
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    billing_cycle = Column(String, nullable=False)  # ожидается "monthly" или "yearly"
    next_payment_date = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="subscriptions")

