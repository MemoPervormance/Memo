"""HWID routes — view, owner-only reset."""
from __future__ import annotations
from datetime import datetime
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import webhooks
from database import get_db
from dependencies import get_current_user, require_owner, require_admin
from models import User, UserHwid, HwidResetLog, HwidViolation, AdminLog
from schemas import (
    HwidOut, HwidResetRequest, HwidResetLogOut,
    HwidViolationOut, MessageResponse, PaginatedResponse,
)

router = APIRouter(prefix="/hwid", tags=["hwid"])


def _log_admin(db: Session, admin_id, action: str, target_id=None, details: str = "") -> None:
    db.add(AdminLog(admin_id=admin_id, action=action, target_user=target_id, details=details))
    db.commit()


# ---------------------------------------------------------------------------
# GET /hwid/me  — user's own HWID
# ---------------------------------------------------------------------------

@router.get("/me", response_model=HwidOut)
def my_hwid(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    hwid = (
        db.query(UserHwid)
        .filter(UserHwid.user_id == current_user.id, UserHwid.is_active.is_(True))
        .first()
    )
    if not hwid:
        raise HTTPException(404, "No HWID bound yet")
    return hwid


# ---------------------------------------------------------------------------
# GET /hwid/user/{user_id}  — admin: view any user's HWID
# ---------------------------------------------------------------------------

@router.get("/user/{user_id}", response_model=List[HwidOut], dependencies=[Depends(require_admin)])
def get_user_hwids(user_id: str, db: Session = Depends(get_db)):
    return db.query(UserHwid).filter(UserHwid.user_id == user_id).all()


# ---------------------------------------------------------------------------
# POST /hwid/reset  — OWNER ONLY
# Clears the active HWID so user can bind a new one on next login.
# ---------------------------------------------------------------------------

@router.post("/reset", response_model=MessageResponse)
def reset_hwid(
    body: HwidResetRequest,
    db: Session = Depends(get_db),
    owner: User = Depends(require_owner),
):
    target_user = db.get(User, str(body.user_id))
    if not target_user:
        raise HTTPException(404, "User not found")

    active_hwid = (
        db.query(UserHwid)
        .filter(UserHwid.user_id == body.user_id, UserHwid.is_active.is_(True))
        .first()
    )
    if not active_hwid:
        raise HTTPException(400, "User has no active HWID")

    old_hash = active_hwid.hwid_hash

    # Deactivate current HWID
    active_hwid.is_active = False
    active_hwid.last_reset = datetime.utcnow()
    active_hwid.reset_count += 1

    # Write reset log
    db.add(HwidResetLog(
        user_id=body.user_id,
        reset_by=owner.id,
        old_hwid=old_hash,
        new_hwid=None,   # will be set when user logs in and rebinds
        reason=body.reason,
    ))
    db.commit()

    _log_admin(db, owner.id, "hwid_reset", body.user_id, f"reason: {body.reason}")
    webhooks.fire("HWID_RESET", {
        "target_user": target_user.username,
        "reset_by": owner.username,
        "reason": body.reason or "—",
    }, db)

    return MessageResponse(message=f"HWID reset for user '{target_user.username}'")


# ---------------------------------------------------------------------------
# GET /hwid/reset-logs  — admin: list all reset logs
# ---------------------------------------------------------------------------

@router.get("/reset-logs", response_model=PaginatedResponse, dependencies=[Depends(require_admin)])
def list_reset_logs(
    db: Session = Depends(get_db),
    page: int = 1,
    per_page: int = 20,
):
    q = db.query(HwidResetLog).order_by(HwidResetLog.created_at.desc())
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    return PaginatedResponse(
        total=total, page=page, per_page=per_page,
        items=[HwidResetLogOut.model_validate(r) for r in items],
    )


# ---------------------------------------------------------------------------
# GET /hwid/violations  — admin: list HWID violations
# ---------------------------------------------------------------------------

@router.get("/violations", response_model=PaginatedResponse, dependencies=[Depends(require_admin)])
def list_violations(
    db: Session = Depends(get_db),
    page: int = 1,
    per_page: int = 20,
):
    q = db.query(HwidViolation).order_by(HwidViolation.created_at.desc())
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    return PaginatedResponse(
        total=total, page=page, per_page=per_page,
        items=[HwidViolationOut.model_validate(v) for v in items],
    )
