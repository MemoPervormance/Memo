"""Subscription routes — view own subscription, admin list."""
from __future__ import annotations
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user, require_admin, Pagination
from models import User, Subscription
from schemas import SubscriptionOut, PaginatedResponse

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/me", response_model=List[SubscriptionOut])
def my_subscriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Subscription)
        .filter(Subscription.user_id == current_user.id)
        .order_by(Subscription.started_at.desc())
        .all()
    )


@router.get("/me/active", response_model=SubscriptionOut)
def my_active_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from datetime import datetime
    sub = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == current_user.id,
            Subscription.is_active.is_(True),
        )
        .first()
    )
    if not sub:
        raise HTTPException(404, "No active subscription")
    # Auto-expire check
    if sub.expires_at and sub.expires_at < datetime.utcnow():
        sub.is_active = False
        db.commit()
        raise HTTPException(404, "Subscription has expired")
    return sub


@router.get("", response_model=PaginatedResponse, dependencies=[Depends(require_admin)])
def list_all_subscriptions(
    db: Session = Depends(get_db),
    pag: Pagination = Depends(),
):
    q = db.query(Subscription).order_by(Subscription.started_at.desc())
    total = q.count()
    items = q.offset(pag.offset).limit(pag.per_page).all()
    return PaginatedResponse(
        total=total, page=pag.page, per_page=pag.per_page,
        items=[SubscriptionOut.model_validate(s) for s in items],
    )


@router.patch("/{sub_id}/deactivate", response_model=SubscriptionOut)
def deactivate_subscription(
    sub_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    sub = db.get(Subscription, sub_id)
    if not sub:
        raise HTTPException(404, "Subscription not found")
    sub.is_active = False
    db.commit()
    db.refresh(sub)
    return sub
