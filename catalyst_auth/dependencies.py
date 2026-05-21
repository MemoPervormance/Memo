"""FastAPI dependencies — current user extraction, role guards, pagination."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, Header, HTTPException, Query, status
from sqlalchemy.orm import Session

from auth import decode_access_token, hash_api_token
from database import get_db
from models import User, ApiToken, ActiveSession


# ---------------------------------------------------------------------------
# Token extraction
# ---------------------------------------------------------------------------

def _bearer_token(authorization: Optional[str] = Header(None)) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return None


# ---------------------------------------------------------------------------
# Current user — JWT or API token
# ---------------------------------------------------------------------------

def get_current_user(
    token: Optional[str] = Depends(_bearer_token),
    db: Session = Depends(get_db),
) -> User:
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")

    # Try JWT first
    payload = decode_access_token(token)
    if payload:
        user = db.get(User, payload["sub"])
        if not user or user.is_banned:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid session")
        return user

    # Try API token (opaque)
    token_hash = hash_api_token(token)
    api_tok = (
        db.query(ApiToken)
        .filter(
            ApiToken.token_hash == token_hash,
            ApiToken.revoked.is_(False),
        )
        .first()
    )
    if not api_tok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    if api_tok.expires_at and api_tok.expires_at < datetime.now(timezone.utc).replace(tzinfo=None):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired")
    user = db.get(User, api_tok.user_id)
    if not user or user.is_banned:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    return user


# ---------------------------------------------------------------------------
# Role guards
# ---------------------------------------------------------------------------

def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in ("admin", "owner"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin access required")
    return user


def require_owner(user: User = Depends(get_current_user)) -> User:
    if user.role != "owner":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Owner access required")
    return user


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

class Pagination:
    def __init__(
        self,
        page:     int = Query(default=1,   ge=1),
        per_page: int = Query(default=20,  ge=1, le=200),
    ) -> None:
        self.page     = page
        self.per_page = per_page
        self.offset   = (page - 1) * per_page
