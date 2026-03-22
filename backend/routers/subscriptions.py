from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import crud, models, schemas
from ..auth import get_current_user
from ..database import get_db

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/", response_model=List[schemas.SubscriptionOut])
def list_subscriptions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    subs = crud.get_subscriptions_for_user(db, user_id=current_user.id)
    return subs


@router.post("/", response_model=schemas.SubscriptionOut, status_code=status.HTTP_201_CREATED)
def create_subscription(
    subscription_in: schemas.SubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    subscription = crud.create_subscription(db, user_id=current_user.id, subscription_in=subscription_in)
    return subscription


@router.put("/{subscription_id}", response_model=schemas.SubscriptionOut)
def update_subscription(
    subscription_id: int,
    subscription_in: schemas.SubscriptionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    updated = crud.update_subscription_for_user(
        db, subscription_id=subscription_id, user_id=current_user.id, subscription_in=subscription_in
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    return updated


@router.delete("/{subscription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    ok = crud.delete_subscription_for_user(db, subscription_id=subscription_id, user_id=current_user.id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found")
    return None

