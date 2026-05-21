"""System settings + admin logs + webhook logs — owner/admin routes."""
from __future__ import annotations
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from dependencies import require_admin, require_owner, Pagination
from models import SystemSetting, AdminLog, WebhookLog
from schemas import (
    SettingOut, SettingUpdateRequest, AdminLogOut,
    WebhookLogOut, MessageResponse, PaginatedResponse,
)

router = APIRouter(prefix="/settings", tags=["settings"])


# ---------------------------------------------------------------------------
# System Settings  (owner only for write, admin for read)
# ---------------------------------------------------------------------------

@router.get("", response_model=List[SettingOut], dependencies=[Depends(require_admin)])
def list_settings(db: Session = Depends(get_db)):
    return db.query(SystemSetting).order_by(SystemSetting.setting_key).all()


@router.get("/{key}", response_model=SettingOut, dependencies=[Depends(require_admin)])
def get_setting(key: str, db: Session = Depends(get_db)):
    s = db.query(SystemSetting).filter(SystemSetting.setting_key == key).first()
    if not s:
        raise HTTPException(404, "Setting not found")
    return s


@router.put("/{key}", response_model=SettingOut)
def update_setting(
    key: str,
    body: SettingUpdateRequest,
    db: Session = Depends(get_db),
    _owner=Depends(require_owner),
):
    s = db.query(SystemSetting).filter(SystemSetting.setting_key == key).first()
    if not s:
        # Create if not exists
        s = SystemSetting(setting_key=key, setting_value=body.setting_value)
        db.add(s)
    else:
        s.setting_value = body.setting_value
        s.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(s)
    return s


# ---------------------------------------------------------------------------
# Admin Logs  (admin read-only)
# ---------------------------------------------------------------------------

@router.get("/admin-logs/all", response_model=PaginatedResponse, dependencies=[Depends(require_admin)])
def list_admin_logs(
    db: Session = Depends(get_db),
    pag: Pagination = Depends(),
):
    q = db.query(AdminLog).order_by(AdminLog.created_at.desc())
    total = q.count()
    items = q.offset(pag.offset).limit(pag.per_page).all()
    return PaginatedResponse(
        total=total, page=pag.page, per_page=pag.per_page,
        items=[AdminLogOut.model_validate(l) for l in items],
    )


# ---------------------------------------------------------------------------
# Webhook Logs  (admin read-only)
# ---------------------------------------------------------------------------

@router.get("/webhook-logs/all", response_model=PaginatedResponse, dependencies=[Depends(require_admin)])
def list_webhook_logs(
    db: Session = Depends(get_db),
    pag: Pagination = Depends(),
):
    q = db.query(WebhookLog).order_by(WebhookLog.created_at.desc())
    total = q.count()
    items = q.offset(pag.offset).limit(pag.per_page).all()
    return PaginatedResponse(
        total=total, page=pag.page, per_page=pag.per_page,
        items=[WebhookLogOut.model_validate(l) for l in items],
    )
