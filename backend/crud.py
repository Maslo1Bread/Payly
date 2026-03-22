from typing import List, Optional

import base64
import hashlib
import hmac
import secrets

from sqlalchemy.orm import Session

from . import models, schemas


_PBKDF2_ALG = "sha256"
_PBKDF2_ITERS = 310_000
_SALT_BYTES = 16


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(_PBKDF2_ALG, password.encode("utf-8"), salt, _PBKDF2_ITERS)
    return "$".join(
        [
            f"pbkdf2_{_PBKDF2_ALG}",
            str(_PBKDF2_ITERS),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(dk).decode("ascii"),
        ]
    )


def _verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, iters_s, salt_b64, dk_b64 = encoded.split("$", 3)
        if not scheme.startswith("pbkdf2_"):
            return False
        alg = scheme.removeprefix("pbkdf2_")
        iters = int(iters_s)
        salt = base64.urlsafe_b64decode(salt_b64.encode("ascii"))
        expected = base64.urlsafe_b64decode(dk_b64.encode("ascii"))
    except Exception:
        return False

    dk = hashlib.pbkdf2_hmac(alg, password.encode("utf-8"), salt, iters)
    return hmac.compare_digest(dk, expected)


# ===== Пользователи =====


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, user_in: schemas.UserCreate) -> models.User:
    password_hash = _hash_password(user_in.password)
    user = models.User(email=user_in.email, password=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[models.User]:
    user = get_user_by_email(db, email=email)
    if not user:
        return None
    stored = user.password or ""
    # Backward compatibility: early project versions stored plaintext passwords.
    if stored.startswith("pbkdf2_"):
        if not _verify_password(password, stored):
            return None
    else:
        if stored != password:
            return None
        # Upgrade to hashed password on successful login.
        user.password = _hash_password(password)
        db.commit()
        db.refresh(user)
    return user


# ===== Подписки =====


def create_subscription(
    db: Session, user_id: int, subscription_in: schemas.SubscriptionCreate
) -> models.Subscription:
    subscription = models.Subscription(
        user_id=user_id,
        name=subscription_in.name,
        price=subscription_in.price,
        billing_cycle=subscription_in.billing_cycle,
        next_payment_date=subscription_in.next_payment_date,
    )
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def get_subscriptions_for_user(db: Session, user_id: int) -> List[models.Subscription]:
    return (
        db.query(models.Subscription)
        .filter(models.Subscription.user_id == user_id)
        .order_by(models.Subscription.created_at.desc())
        .all()
    )


def get_subscription_by_id_for_user(
    db: Session, subscription_id: int, user_id: int
) -> Optional[models.Subscription]:
    return (
        db.query(models.Subscription)
        .filter(
            models.Subscription.id == subscription_id,
            models.Subscription.user_id == user_id,
        )
        .first()
    )


def update_subscription_for_user(
    db: Session,
    subscription_id: int,
    user_id: int,
    subscription_in: schemas.SubscriptionUpdate,
) -> Optional[models.Subscription]:
    subscription = get_subscription_by_id_for_user(db, subscription_id, user_id)
    if not subscription:
        return None

    data = subscription_in.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(subscription, field, value)

    db.commit()
    db.refresh(subscription)
    return subscription


def delete_subscription_for_user(db: Session, subscription_id: int, user_id: int) -> bool:
    subscription = get_subscription_by_id_for_user(db, subscription_id, user_id)
    if not subscription:
        return False
    db.delete(subscription)
    db.commit()
    return True

