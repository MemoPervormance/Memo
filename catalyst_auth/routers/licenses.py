"""License key routes — create (admin), list, validate, status management."""
from __future__ import annotations
import secrets
import string
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

import webhooks
from database import get_db
from dependencies import get_current_user, require_admin
from models import LicenseKey, User, AdminLog
from schemas import (
    LicenseKeyOut, LicenseCreateRequest, LicenseStatusUpdateRequest,
    MessageResponse, PaginatedResponse,
)

router = APIRouter(prefix="/licenses", tags=["licenses"])

_PLAN_DAYS = {
    "1day":    1,
    "1week":   7,
    "1month":  30,
    "3month":  90,
    "6month":  180,
    "lifetime": None,
}


def _gen_key() -> str:
    """Generate a Catalyst-style license key: XXXX-XXXX-XXXX-XXXX."""
    chars = string.ascii_uppercase + string.digits
    groups = ["".join(secrets.choice(chars) for _ in range(4)) for _ in range(4)]
    return "-".join(groups)


def _log_admin(db: Session, admin_id, action: str, target_id=None, details: str = "") -> None:
    db.add(AdminLog(admin_id=admin_id, action=action, target_user=target_id, details=details))
    db.commit()


# ---------------------------------------------------------------------------
# POST /licenses  — admin: create one or many keys
# ---------------------------------------------------------------------------

@router.post("", response_model=List[LicenseKeyOut])
def create_licenses(
    body: LicenseCreateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if body.plan_type not in _PLAN_DAYS:
        raise HTTPException(400, f"Unknown plan_type. Valid: {list(_PLAN_DAYS)}")

    created: List[LicenseKey] = []
    for _ in range(body.count):
        key_str = _gen_key()
        # Collision retry
        while db.query(LicenseKey).filter(LicenseKey.license_key == key_str).first():
            key_str = _gen_key()

        lic = LicenseKey(
            license_key=key_str,
            plan_type=body.plan_type,
            duration_days=_PLAN_DAYS[body.plan_type],
            status="unused",
            created_by=admin.id,
            notes=body.notes,
        )
        db.add(lic)
        created.append(lic)

    db.commit()
    for lic in created:
        db.refresh(lic)

    _log_admin(db, admin.id, "create_license_keys",
               details=f"plan={body.plan_type} count={body.count}")
    return [LicenseKeyOut.model_validate(lic) for lic in created]


# ---------------------------------------------------------------------------
# GET /licenses  — admin: list all
# ---------------------------------------------------------------------------

@router.get("", response_model=PaginatedResponse, dependencies=[Depends(require_admin)])
def list_licenses(
    status: str = None,
    plan_type: str = None,
    db: Session = Depends(get_db),
    page: int = 1,
    per_page: int = 20,
):
    q = db.query(LicenseKey).order_by(LicenseKey.created_at.desc())
    if status:
        q = q.filter(LicenseKey.status == status)
    if plan_type:
        q = q.filter(LicenseKey.plan_type == plan_type)
    total = q.count()
    items = q.offset((page - 1) * per_page).limit(per_page).all()
    return PaginatedResponse(
        total=total, page=page, per_page=per_page,
        items=[LicenseKeyOut.model_validate(l) for l in items],
    )


# ---------------------------------------------------------------------------
# GET /licenses/{key}  — admin: lookup single key
# ---------------------------------------------------------------------------

@router.get("/{key_str}", response_model=LicenseKeyOut, dependencies=[Depends(require_admin)])
def get_license(key_str: str, db: Session = Depends(get_db)):
    lic = db.query(LicenseKey).filter(LicenseKey.license_key == key_str).first()
    if not lic:
        raise HTTPException(404, "License key not found")
    return lic


# ---------------------------------------------------------------------------
# PATCH /licenses/{key}/status  — admin: change status
# ---------------------------------------------------------------------------

@router.patch("/{key_str}/status", response_model=LicenseKeyOut)
def update_license_status(
    key_str: str,
    body: LicenseStatusUpdateRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    valid_statuses = {"unused", "active", "expired", "banned", "paused"}
    if body.status not in valid_statuses:
        raise HTTPException(400, f"Invalid status. Valid: {valid_statuses}")

    lic = db.query(LicenseKey).filter(LicenseKey.license_key == key_str).first()
    if not lic:
        raise HTTPException(404, "License key not found")

    lic.status = body.status
    db.commit()
    db.refresh(lic)

    _log_admin(db, admin.id, "update_license_status",
               details=f"key={key_str} status={body.status}")
    return lic


# ---------------------------------------------------------------------------
# DELETE /licenses/{key}  — admin: delete unused key
# ---------------------------------------------------------------------------

@router.delete("/{key_str}", response_model=MessageResponse)
def delete_license(
    key_str: str,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    lic = db.query(LicenseKey).filter(LicenseKey.license_key == key_str).first()
    if not lic:
        raise HTTPException(404, "License key not found")
    if lic.status not in ("unused", "expired", "banned"):
        raise HTTPException(400, "Can only delete unused/expired/banned keys")
    db.delete(lic)
    db.commit()
    _log_admin(db, admin.id, "delete_license", details=f"key={key_str}")
    return MessageResponse(message="License key deleted")


# ---------------------------------------------------------------------------
# POST /licenses/validate  — public: validate a key + HWID
# ---------------------------------------------------------------------------

@router.post("/validate", response_model=MessageResponse)
def validate_license(
    license_key: str,
    hwid_hash: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lic = db.query(LicenseKey).filter(
        LicenseKey.license_key == license_key,
        LicenseKey.user_id == current_user.id,
    ).first()
    if not lic:
        raise HTTPException(404, "License not found for this account")
    if lic.status == "banned":
        raise HTTPException(403, "License is banned")
    if lic.status == "paused":
        raise HTTPException(403, "License is paused")
    if lic.status == "expired":
        raise HTTPException(403, "License is expired")
    if lic.expires_at and lic.expires_at < datetime.utcnow():
        lic.status = "expired"
        db.commit()
        raise HTTPException(403, "License has expired")
    if hwid_hash and lic.bound_hwid and lic.bound_hwid != hwid_hash:
        raise HTTPException(403, "HWID does not match license")
    if hwid_hash:
        lic.last_ip = None  # tracked separately; update bound_hwid only if not set
        if not lic.bound_hwid:
            lic.bound_hwid = hwid_hash
        db.commit()
    return MessageResponse(message=f"License valid — plan: {lic.plan_type}")
