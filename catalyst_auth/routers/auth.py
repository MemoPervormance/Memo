"""Auth routes — register, login, logout, validate-token."""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

import auth as auth_utils
import webhooks
from database import get_db
from dependencies import get_current_user
from models import (
    User, UserHwid, LoginLog, ActiveSession, HwidViolation, Subscription
)
from schemas import (
    LoginRequest, RegisterRequest, TokenResponse,
    LicenseActivateRequest, MessageResponse, UserOut,
)

router = APIRouter(prefix="/auth", tags=["auth"])

ACCESS_MINUTES = auth_utils.ACCESS_TOKEN_EXPIRE_MINUTES


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _write_login_log(
    db: Session, user_id, ip: str, ua: str,
    success: bool, reason: Optional[str] = None,
) -> None:
    db.add(LoginLog(
        user_id=user_id, ip_address=ip,
        user_agent=ua, success=success, reason=reason,
    ))
    db.commit()


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------

@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(400, "Username already taken")
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(400, "Email already registered")

    user = User(
        username=body.username,
        email=body.email,
        password_hash=auth_utils.hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return MessageResponse(message="Registration successful")


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------

@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = _client_ip(request)
    ua = request.headers.get("User-Agent", "")

    user = db.query(User).filter(User.username == body.username).first()

    if not user or not auth_utils.verify_password(body.password, user.password_hash):
        if user:
            _write_login_log(db, user.id, ip, ua, False, "invalid_password")
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    if user.is_banned:
        _write_login_log(db, user.id, ip, ua, False, "banned")
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account banned")

    # HWID check (if client sends hwid_hash)
    if body.hwid_hash:
        active_hwid = (
            db.query(UserHwid)
            .filter(UserHwid.user_id == user.id, UserHwid.is_active.is_(True))
            .first()
        )
        if active_hwid is None:
            # First bind
            hwid = UserHwid(
                user_id=user.id,
                hwid_hash=body.hwid_hash,
                cpu_id=body.cpu_id,
                motherboard_serial=body.motherboard_serial,
                disk_serial=body.disk_serial,
                mac_address=body.mac_address,
            )
            db.add(hwid)
            db.commit()
        elif active_hwid.hwid_hash != body.hwid_hash:
            # HWID mismatch → log violation
            db.add(HwidViolation(
                user_id=user.id,
                attempted_hwid=body.hwid_hash,
                registered_hwid=active_hwid.hwid_hash,
                ip_address=ip,
            ))
            db.commit()
            _write_login_log(db, user.id, ip, ua, False, "hwid_mismatch")
            webhooks.fire("HWID_VIOLATION", {
                "user": user.username,
                "ip": ip,
            }, db)
            raise HTTPException(status.HTTP_403_FORBIDDEN, "HWID mismatch")
        else:
            active_hwid.last_seen = datetime.utcnow()
            db.commit()

    # Subscription check — warn but don't block login
    active_sub = (
        db.query(Subscription)
        .filter(
            Subscription.user_id == user.id,
            Subscription.is_active.is_(True),
            Subscription.expires_at > datetime.utcnow(),
        )
        .first()
    )

    token = auth_utils.create_access_token(str(user.id), user.role)

    # Update last_login
    user.last_login = datetime.utcnow()
    db.commit()

    # Session record
    session_tok = auth_utils.generate_session_token()
    db.add(ActiveSession(
        user_id=user.id,
        session_token=session_tok,
        ip_address=ip,
        device_name=ua[:200] if ua else None,
        expires_at=datetime.utcnow() + timedelta(minutes=ACCESS_MINUTES),
    ))
    db.commit()

    _write_login_log(db, user.id, ip, ua, True)
    webhooks.fire("LOGIN", {"user": user.username, "ip": ip}, db)

    return TokenResponse(
        access_token=token,
        expires_in=ACCESS_MINUTES * 60,
    )


# ---------------------------------------------------------------------------
# POST /auth/logout
# ---------------------------------------------------------------------------

@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Invalidate all active sessions for this user
    db.query(ActiveSession).filter(
        ActiveSession.user_id == current_user.id,
        ActiveSession.is_active.is_(True),
    ).update({"is_active": False})
    db.commit()
    return MessageResponse(message="Logged out")


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------

@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


# ---------------------------------------------------------------------------
# POST /auth/activate-license
# ---------------------------------------------------------------------------

@router.post("/activate-license", response_model=MessageResponse)
def activate_license(
    body: LicenseActivateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from models import LicenseKey, Subscription
    from datetime import timedelta

    _PLAN_DAYS = {
        "1day":    1,
        "1week":   7,
        "1month":  30,
        "3month":  90,
        "6month":  180,
        "lifetime": None,
    }

    lic = db.query(LicenseKey).filter(LicenseKey.license_key == body.license_key).first()
    if not lic:
        raise HTTPException(404, "License key not found")
    if lic.status != "unused":
        raise HTTPException(400, f"License is '{lic.status}', cannot activate")

    now = datetime.utcnow()
    days = _PLAN_DAYS.get(lic.plan_type)
    expires = (now + timedelta(days=days)) if days else None

    lic.user_id = current_user.id
    lic.status = "active"
    lic.activated_at = now
    lic.expires_at = expires
    if body.hwid_hash:
        lic.bound_hwid = body.hwid_hash

    sub = Subscription(
        user_id=current_user.id,
        license_id=lic.id,
        subscription_type=lic.plan_type,
        started_at=now,
        expires_at=expires,
        is_active=True,
    )
    db.add(sub)
    db.commit()

    webhooks.fire("LICENSE_ACTIVATED", {
        "user":  current_user.username,
        "plan":  lic.plan_type,
        "key":   lic.license_key,
    }, db)

    return MessageResponse(message=f"License activated — plan: {lic.plan_type}")
