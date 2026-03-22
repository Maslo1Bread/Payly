from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, schemas
from ..auth import create_access_token, get_bearer_token, get_current_user, revoke_token
from ..database import get_db

router = APIRouter(tags=["auth"])


@router.post("/register", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: schemas.UserCreate, db: Session = Depends(get_db)):
    existing_user = crud.get_user_by_email(db, user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists",
        )

    user = crud.create_user(db, user_in)
    return user


@router.post("/login", response_model=schemas.Token)
def login(user_in: schemas.UserLogin, db: Session = Depends(get_db)):
    user = crud.authenticate_user(db, email=user_in.email, password=user_in.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    token = create_access_token(user.id)
    return schemas.Token(access_token=token)


@router.get("/me", response_model=schemas.UserOut)
def me(current_user=Depends(get_current_user)):
    return current_user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(token: str = Depends(get_bearer_token)):
    revoke_token(token)
    return None
