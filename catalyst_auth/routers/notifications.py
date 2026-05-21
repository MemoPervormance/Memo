"""Notification routes — user inbox + admin broadcast."""
from __future__ import annotations
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user, require_admin, Pagination
from models import User, Notification
from schemas import NotificationOut, NotificationCreateRequest, MessageResponse, PaginatedResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/me", response_model=List[NotificationOut])
def my_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    unread_only: bool = False,
):
    q = db.query(Notification).filter(Notification.user_id == current_user.id)
    if unread_only:
        q = q.filter(Notification.is_read.is_(False))
    return q.order_by(Notification.created_at.desc()).all()


@router.post("/me/{notification_id}/read", response_model=MessageResponse)
def mark_read(
    notification_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    n = db.get(Notification, notification_id)
    if not n or str(n.user_id) != str(current_user.id):
        raise HTTPException(404, "Notification not found")
    n.is_read = True
    db.commit()
    return MessageResponse(message="Marked as read")


@router.post("/me/read-all", response_model=MessageResponse)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read.is_(False),
    ).update({"is_read": True})
    db.commit()
    return MessageResponse(message="All notifications marked as read")


# Admin: send to specific user
@router.post("", response_model=NotificationOut)
def send_notification(
    body: NotificationCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    target = db.get(User, str(body.user_id))
    if not target:
        raise HTTPException(404, "Target user not found")
    n = Notification(user_id=body.user_id, title=body.title, message=body.message)
    db.add(n)
    db.commit()
    db.refresh(n)
    return n


# Admin: broadcast to all users
@router.post("/broadcast", response_model=MessageResponse)
def broadcast_notification(
    title: str,
    message: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    users = db.query(User).filter(User.is_banned.is_(False)).all()
    for u in users:
        db.add(Notification(user_id=u.id, title=title, message=message))
    db.commit()
    return MessageResponse(message=f"Broadcast sent to {len(users)} users")


# Admin: list all
@router.get("", response_model=PaginatedResponse, dependencies=[Depends(require_admin)])
def list_all_notifications(
    db: Session = Depends(get_db),
    pag: Pagination = Depends(),
):
    q = db.query(Notification).order_by(Notification.created_at.desc())
    total = q.count()
    items = q.offset(pag.offset).limit(pag.per_page).all()
    return PaginatedResponse(
        total=total, page=pag.page, per_page=pag.per_page,
        items=[NotificationOut.model_validate(n) for n in items],
    )
