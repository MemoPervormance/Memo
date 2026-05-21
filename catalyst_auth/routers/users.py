"""User management routes — self-service + admin."""
from __future__ import annotations
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import auth as auth_utils
from database import get_db
from dependencies import get_current_user, require_admin, Pagination
from models import User, AdminLog
from schemas import (
    UserOut, UserUpdateRequest, AdminUserUpdateRequest,
    MessageResponse, PaginatedResponse,
)

router = APIRouter(prefix="/users", tags=["users"])


def _write_admin_log(db: Session, admin_id, action: str, target_id=None, details: str = "") -> None:
    db.add(AdminLog(admin_id=admin_id, action=action, target_user=target_id, details=details))
    db.commit()


# ---------------------------------------------------------------------------
# GET /users/me  (alias — handled in auth router too)
# PATCH /users/me
# ---------------------------------------------------------------------------

@router.patch("/me", response_model=UserOut)
def update_self(
    body: UserUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.email and body.email != current_user.email:
        if db.query(User).filter(User.email == body.email).first():
            raise HTTPException(400, "Email already in use")
        current_user.email = body.email
    if body.avatar_url is not None:
        current_user.avatar_url = body.avatar_url
    if body.discord_id is not None:
        current_user.discord_id = body.discord_id
    if body.telegram_id is not None:
        current_user.telegram_id = body.telegram_id
    if body.notes is not None:
        current_user.notes = body.notes
    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/me/change-password", response_model=MessageResponse)
def change_password(
    old_password: str,
    new_password: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not auth_utils.verify_password(old_password, current_user.password_hash):
        raise HTTPException(400, "Old password is incorrect")
    if len(new_password) < 8:
        raise HTTPException(400, "New password must be at least 8 characters")
    current_user.password_hash = auth_utils.hash_password(new_password)
    db.commit()
    return MessageResponse(message="Password changed")


# ---------------------------------------------------------------------------
# Admin routes
# ---------------------------------------------------------------------------

@router.get("", response_model=PaginatedResponse, dependencies=[Depends(require_admin)])
def list_users(
    db: Session = Depends(get_db),
    pag: Pagination = Depends(),
):
    q = db.query(User)
    total = q.count()
    items = q.offset(pag.offset).limit(pag.per_page).all()
    return PaginatedResponse(
        total=total, page=pag.page, per_page=pag.per_page,
        items=[UserOut.model_validate(u) for u in items],
    )


@router.get("/{user_id}", response_model=UserOut, dependencies=[Depends(require_admin)])
def get_user(user_id: str, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user


@router.patch("/{user_id}", response_model=UserOut)
def admin_update_user(
    user_id: str,
    body: AdminUserUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if user.role == "owner" and admin.role != "owner":
        raise HTTPException(403, "Cannot modify owner account")

    changes: list[str] = []
    if body.role is not None:
        if body.role == "owner" and admin.role != "owner":
            raise HTTPException(403, "Only owner can assign owner role")
        user.role = body.role
        changes.append(f"role={body.role}")
    if body.is_banned is not None:
        user.is_banned = body.is_banned
        changes.append(f"banned={body.is_banned}")
    if body.is_verified is not None:
        user.is_verified = body.is_verified
        changes.append(f"verified={body.is_verified}")
    if body.notes is not None:
        user.notes = body.notes

    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    _write_admin_log(db, admin.id, "update_user", user.id, "; ".join(changes))
    return user


@router.delete("/{user_id}", response_model=MessageResponse)
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    if user.role == "owner":
        raise HTTPException(403, "Cannot delete owner account")
    db.delete(user)
    db.commit()
    _write_admin_log(db, admin.id, "delete_user", None, f"deleted user {user_id}")
    return MessageResponse(message="User deleted")
