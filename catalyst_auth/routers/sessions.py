"""Session management routes."""
from __future__ import annotations
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_user, require_admin, Pagination
from models import User, ActiveSession, LoginLog
from schemas import SessionOut, LoginLogOut, MessageResponse, PaginatedResponse

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("/me", response_model=List[SessionOut])
def my_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(ActiveSession)
        .filter(ActiveSession.user_id == current_user.id, ActiveSession.is_active.is_(True))
        .all()
    )


@router.delete("/me/all", response_model=MessageResponse)
def revoke_all_my_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.query(ActiveSession).filter(
        ActiveSession.user_id == current_user.id,
        ActiveSession.is_active.is_(True),
    ).update({"is_active": False})
    db.commit()
    return MessageResponse(message="All sessions revoked")


@router.delete("/{session_id}", response_model=MessageResponse)
def revoke_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    s = db.get(ActiveSession, session_id)
    if not s or str(s.user_id) != str(current_user.id):
        raise HTTPException(404, "Session not found")
    s.is_active = False
    db.commit()
    return MessageResponse(message="Session revoked")


# Admin: all sessions
@router.get("", response_model=PaginatedResponse, dependencies=[Depends(require_admin)])
def list_sessions(
    db: Session = Depends(get_db),
    pag: Pagination = Depends(),
):
    q = db.query(ActiveSession).order_by(ActiveSession.created_at.desc())
    total = q.count()
    items = q.offset(pag.offset).limit(pag.per_page).all()
    return PaginatedResponse(
        total=total, page=pag.page, per_page=pag.per_page,
        items=[SessionOut.model_validate(s) for s in items],
    )


# Login logs
@router.get("/logs/me", response_model=List[LoginLogOut])
def my_login_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 50,
):
    return (
        db.query(LoginLog)
        .filter(LoginLog.user_id == current_user.id)
        .order_by(LoginLog.created_at.desc())
        .limit(limit)
        .all()
    )


@router.get("/logs/all", response_model=PaginatedResponse, dependencies=[Depends(require_admin)])
def all_login_logs(
    db: Session = Depends(get_db),
    pag: Pagination = Depends(),
):
    q = db.query(LoginLog).order_by(LoginLog.created_at.desc())
    total = q.count()
    items = q.offset(pag.offset).limit(pag.per_page).all()
    return PaginatedResponse(
        total=total, page=pag.page, per_page=pag.per_page,
        items=[LoginLogOut.model_validate(l) for l in items],
    )
