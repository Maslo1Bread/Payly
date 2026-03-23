import secrets
from pathlib import Path

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from . import crud, models
from .database import get_db
from .token_store import EncryptedTokenStore


_BACKEND_DIR = Path(__file__).resolve().parent
_TOKEN_KEY_PATH = _BACKEND_DIR / ".token_store.key"
_TOKENS_DATA_PATH = _BACKEND_DIR / ".token_store.enc"
TOKENS = EncryptedTokenStore(key_path=_TOKEN_KEY_PATH, data_path=_TOKENS_DATA_PATH)

security_scheme = HTTPBearer(auto_error=False)

def get_bearer_token(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> str:
    """
    Достаёт bearer-токен из заголовка Authorization.
    """
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    return credentials.credentials


def create_access_token(user_id: int) -> str:
    """
    Генерирует простой случайный токен и сохраняет его постоянно (в зашифрованном файле).
    """
    token = secrets.token_hex(32)
    TOKENS.set_token(token, user_id)
    return token


def revoke_token(token: str) -> None:
    """
    Инвалидирует токен (удаляет из постоянного хранилища).
    """
    TOKENS.revoke(token)


def get_current_user(
    token: str = Depends(get_bearer_token),
    db: Session = Depends(get_db),
) -> models.User:

    user_id = TOKENS.get_user_id(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user

